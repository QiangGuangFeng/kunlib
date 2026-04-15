#!/usr/bin/env Rscript
# run_pedigree.r — Core pedigree analysis pipeline via visPedigree
# Called by pedigree_analysis.py via subprocess.
#
# Modules (controlled by --tasks):
#   stats, inbreeding, interval, diversity, ancestry, matrix, visual

suppressPackageStartupMessages({
  library(visPedigree)
  library(data.table)
  library(jsonlite)
})

# =========================================================================== #
# CLI Argument Parsing
# =========================================================================== #
args <- commandArgs(trailingOnly = TRUE)

parse_arg <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (length(idx) == 0) return(default)
  args[idx + 1]
}

parse_flag <- function(flag) {
  flag %in% args
}

input_file    <- parse_arg("--input-file")
tables_dir    <- parse_arg("--tables-dir", ".")
figures_dir   <- parse_arg("--figures-dir", ".")
work_dir      <- parse_arg("--work-dir", ".")
tasks_str     <- parse_arg("--tasks", "stats,inbreeding,visual")
cand_str      <- parse_arg("--cand")
trace_dir     <- parse_arg("--trace", "up")
tracegen_str  <- parse_arg("--tracegen")
timevar       <- parse_arg("--timevar")
foundervar    <- parse_arg("--foundervar")
reference_str <- parse_arg("--reference")
top_n         <- as.integer(parse_arg("--top", "20"))
mat_method    <- parse_arg("--mat-method", "A")
mat_compact   <- parse_flag("--mat-compact")
export_matrix <- parse_flag("--export-matrix")
vis_compact   <- parse_flag("--compact")
highlight_str <- parse_arg("--highlight")
vis_trace     <- parse_arg("--vis-trace", "up")
showf         <- parse_flag("--showf")
fig_format    <- parse_arg("--fig-format", "pdf")
fig_width     <- as.integer(parse_arg("--fig-width", "12"))
fig_height    <- as.integer(parse_arg("--fig-height", "10"))
breaks_str    <- parse_arg("--inbreed-breaks", "0.0625,0.125,0.25")
threads       <- as.integer(parse_arg("--threads", "0"))

# Parse composite arguments
tasks          <- trimws(strsplit(tasks_str, ",")[[1]])
inbreed_breaks <- as.numeric(strsplit(breaks_str, ",")[[1]])
tracegen_val   <- if (!is.null(tracegen_str)) as.integer(tracegen_str) else NULL

# =========================================================================== #
# Read and Tidy Pedigree
# =========================================================================== #
ped_raw <- fread(input_file, colClasses = "character")
if (ncol(ped_raw) < 3) stop("Pedigree file must have at least 3 columns (Ind, Sire, Dam)")

# Enforce standard column names for first 3 columns
colnames(ped_raw)[1:3] <- c("Ind", "Sire", "Dam")

# Normalise missing-parent codes → NA
for (col in c("Sire", "Dam")) {
  ped_raw[get(col) %in% c("0", "*", ""), (col) := NA_character_]
}

# Convert numeric columns back (Year etc.)
for (cname in names(ped_raw)[-(1:3)]) {
  vals <- ped_raw[[cname]]
  non_na <- vals[!is.na(vals) & vals != "NA"]
  if (length(non_na) > 0 && all(grepl("^-?[0-9]+(\\.[0-9]+)?$", non_na))) {
    ped_raw[, (cname) := as.numeric(get(cname))]
  }
}
# Re-set NA strings to proper NA
for (col in names(ped_raw)) {
  ped_raw[get(col) == "NA", (col) := NA]
}

# Validate timevar / foundervar presence
if (!is.null(timevar) && !timevar %in% names(ped_raw)) {
  message(sprintf("[Warning] timevar '%s' not found in pedigree columns. Ignoring.", timevar))
  timevar <- NULL
}
if (!is.null(foundervar) && !foundervar %in% names(ped_raw)) {
  message(sprintf("[Warning] foundervar '%s' not found in pedigree columns. Ignoring.", foundervar))
  foundervar <- NULL
}

# Main tidy — compute inbreeding if needed by any module
needs_inbreed <- any(c("inbreeding") %in% tasks) || showf
tp <- tidyped(ped_raw, inbreed = needs_inbreed)

# Always save tidied pedigree
fwrite(tp, file.path(tables_dir, "tidyped.csv"))

# =========================================================================== #
# Summary collector  (use an environment so <- works inside tryCatch closures)
# =========================================================================== #
state <- new.env(parent = emptyenv())
state$n_individuals  <- nrow(tp)
state$n_founders     <- sum(is.na(tp$Sire) & is.na(tp$Dam))
state$n_generations  <- max(tp$Gen, na.rm = TRUE) + 1L
state$tasks_executed <- character(0)
state$tasks_skipped  <- character(0)

# Parse highlight IDs once (used by visual module)
highlight_ids <- if (!is.null(highlight_str) && nchar(highlight_str) > 0)
  trimws(strsplit(highlight_str, ",")[[1]]) else NULL

# =========================================================================== #
# Module: stats
# =========================================================================== #
if ("stats" %in% tasks) {
  tryCatch({
    ps <- pedstats(tp, timevar = timevar)
    fwrite(ps$summary, file.path(tables_dir, "pedstats_summary.csv"))
    if (!is.null(ps$ecg)) {
      fwrite(ps$ecg, file.path(tables_dir, "pedstats_ecg.csv"))
    }
    # Subpopulation summary
    subpop <- pedsubpop(tp)
    fwrite(subpop, file.path(tables_dir, "subpopulation.csv"))
    # ECG histogram plot
    if (!is.null(ps$ecg)) {
      png(file.path(figures_dir, "ecg_plot.png"), width = 800, height = 600, res = 100)
      p <- plot(ps, type = "ecg")
      print(p)
      dev.off()
    }
    state$stats <- as.list(ps$summary)
    state$tasks_executed <- c(state$tasks_executed, "stats")
    message("[stats] Done.")
  }, error = function(e) {
    message(sprintf("[stats] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped, paste0("stats: ", e$message))
  })
}

# =========================================================================== #
# Module: inbreeding
# =========================================================================== #
if ("inbreeding" %in% tasks) {
  tryCatch({
    # tp already has f column if needs_inbreed was TRUE; otherwise compute now
    if (!"f" %in% names(tp)) {
      tp <- inbreed(tp)
    }
    # Individual-level inbreeding
    inbreed_cols <- c("Ind", "f", "Gen")
    if ("Year" %in% names(tp)) inbreed_cols <- c(inbreed_cols, "Year")
    inbreed_dt <- tp[, ..inbreed_cols]
    fwrite(inbreed_dt, file.path(tables_dir, "inbreeding.csv"))

    # Inbreeding classification
    fclass <- pedfclass(tp, breaks = inbreed_breaks)
    fwrite(fclass, file.path(tables_dir, "inbreeding_class.csv"))

    # Summary stats
    f_vals <- tp$f[!is.na(tp$f)]
    state$inbreeding <- list(
      mean_f   = round(mean(f_vals), 6),
      max_f    = round(max(f_vals), 6),
      n_inbred = sum(f_vals > 0),
      n_total  = length(f_vals)
    )
    state$tasks_executed <- c(state$tasks_executed, "inbreeding")
    message("[inbreeding] Done.")
  }, error = function(e) {
    message(sprintf("[inbreeding] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("inbreeding: ", e$message))
  })
}

# =========================================================================== #
# Module: interval
# =========================================================================== #
if ("interval" %in% tasks) {
  tryCatch({
    if (is.null(timevar)) {
      message("[interval] Skipped: --timevar not provided.")
      state$tasks_skipped <- c(state$tasks_skipped,
                               "interval: no --timevar provided")
    } else {
      gi <- pedgenint(tp, timevar = timevar)
      fwrite(gi, file.path(tables_dir, "gen_intervals.csv"))
      state$gen_intervals <- as.list(gi[Pathway == "Average"])
      state$tasks_executed <- c(state$tasks_executed, "interval")
      message("[interval] Done.")
    }
  }, error = function(e) {
    message(sprintf("[interval] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("interval: ", e$message))
  })
}

# =========================================================================== #
# Module: diversity
# =========================================================================== #
if ("diversity" %in% tasks) {
  tryCatch({
    # Determine reference individuals
    if (!is.null(reference_str) && nchar(reference_str) > 0) {
      ref_ids <- trimws(strsplit(reference_str, ",")[[1]])
    } else {
      # Auto: latest generation
      ref_ids <- tp[Gen == max(Gen, na.rm = TRUE), Ind]
    }

    div <- pediv(tp, reference = ref_ids, top = top_n)

    # Summary table
    div_summary_dt <- as.data.table(div$summary)
    fwrite(div_summary_dt, file.path(tables_dir, "diversity_summary.csv"))

    # Founder contributions
    if (!is.null(div$founders)) {
      fwrite(div$founders, file.path(tables_dir, "founder_contrib.csv"))
    }
    # Ancestor contributions
    if (!is.null(div$ancestors)) {
      fwrite(div$ancestors, file.path(tables_dir, "ancestor_contrib.csv"))
    }

    state$diversity <- as.list(div$summary)
    state$tasks_executed <- c(state$tasks_executed, "diversity")
    message("[diversity] Done.")
  }, error = function(e) {
    message(sprintf("[diversity] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("diversity: ", e$message))
  })
}

# =========================================================================== #
# Module: ancestry
# =========================================================================== #
if ("ancestry" %in% tasks) {
  tryCatch({
    if (is.null(foundervar)) {
      message("[ancestry] Skipped: --foundervar not provided.")
      state$tasks_skipped <- c(state$tasks_skipped,
                               "ancestry: no --foundervar provided")
    } else {
      anc <- pedancestry(tp, foundervar = foundervar)
      fwrite(anc, file.path(tables_dir, "ancestry_proportions.csv"))
      # Count unique founder groups
      group_cols <- setdiff(names(anc), "Ind")
      state$ancestry <- list(
        n_founder_groups = length(group_cols),
        groups           = group_cols
      )
      state$tasks_executed <- c(state$tasks_executed, "ancestry")
      message("[ancestry] Done.")
    }
  }, error = function(e) {
    message(sprintf("[ancestry] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("ancestry: ", e$message))
  })
}

# =========================================================================== #
# Module: matrix
# =========================================================================== #
if ("matrix" %in% tasks) {
  tryCatch({
    n_ind <- nrow(tp)
    effective_compact <- mat_compact

    # Auto-compact for large pedigrees
    if (n_ind > 2000 && !mat_compact) {
      message(sprintf(
        "[matrix] Auto-enabling compact mode (%d individuals > 2000).", n_ind))
      effective_compact <- TRUE
    }

    A <- pedmat(tp, method = mat_method, compact = effective_compact,
                threads = threads)

    # Summary statistics
    s <- summary_pedmat(A)
    summary_dt <- data.table(
      Method       = s$method,
      N_Original   = s$n_original,
      N_Calculated = s$n_calculated,
      Compact      = s$compact
    )
    fwrite(summary_dt, file.path(tables_dir, "matrix_summary.csv"))

    # Heatmap
    heatmap_file <- file.path(figures_dir, "matrix_heatmap.png")
    png(heatmap_file, width = 800, height = 800, res = 100)
    p <- vismat(A)
    print(p)
    dev.off()

    # Export full matrix (optional)
    if (export_matrix) {
      mat_dense <- as.matrix(A)
      mat_dt <- as.data.table(mat_dense, keep.rownames = "Ind")
      fwrite(mat_dt, file.path(tables_dir,
             paste0(tolower(mat_method), "mat.csv")))
    }

    state$matrix <- list(
      method       = s$method,
      n_original   = s$n_original,
      n_calculated = s$n_calculated,
      compact      = s$compact
    )
    state$tasks_executed <- c(state$tasks_executed, "matrix")
    message("[matrix] Done.")
  }, error = function(e) {
    message(sprintf("[matrix] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("matrix: ", e$message))
  })
}

# =========================================================================== #
# Module: visual
# =========================================================================== #
if ("visual" %in% tasks) {
  tryCatch({
    n_ind <- nrow(tp)

    # Determine pedigree subset for visualization
    if (!is.null(cand_str) && nchar(cand_str) > 0) {
      # User-specified candidates
      cand_ids <- trimws(strsplit(cand_str, ",")[[1]])
      tp_vis <- tidyped(ped_raw, cand = cand_ids, trace = vis_trace,
                        tracegen = tracegen_val, inbreed = showf)
      use_compact <- vis_compact
    } else if (n_ind > 500) {
      # Auto-truncate for large pedigrees
      latest_gen <- tp[Gen == max(Gen, na.rm = TRUE)]
      n_auto <- min(5L, nrow(latest_gen))
      auto_cand <- sample(latest_gen$Ind, n_auto)
      tp_vis <- tidyped(ped_raw, cand = auto_cand, trace = "up",
                        tracegen = 3L, inbreed = showf)
      use_compact <- TRUE
      message(sprintf(
        "[visual] Auto-truncated: %d individuals too large. Drawing %d candidates (tracegen=3).",
        n_ind, n_auto))
    } else {
      tp_vis <- tp
      use_compact <- vis_compact
    }

    # Render pedigree graph
    if (fig_format == "pdf") {
      out_file <- file.path(figures_dir, "pedigree.pdf")
      visped(tp_vis, compact = use_compact, showf = showf,
             highlight = highlight_ids,
             file = out_file, showgraph = FALSE)
    } else {
      out_file <- file.path(figures_dir, "pedigree.png")
      png(out_file, width = fig_width * 100, height = fig_height * 100, res = 100)
      visped(tp_vis, compact = use_compact, showf = showf,
             highlight = highlight_ids,
             showgraph = TRUE, file = NULL)
      dev.off()
    }

    state$visual <- list(
      n_drawn    = nrow(tp_vis),
      format     = fig_format,
      compact    = use_compact,
      output     = out_file
    )
    state$tasks_executed <- c(state$tasks_executed, "visual")
    message("[visual] Done.")
  }, error = function(e) {
    message(sprintf("[visual] Error: %s", e$message))
    state$tasks_skipped <- c(state$tasks_skipped,
                              paste0("visual: ", e$message))
  })
}

# =========================================================================== #
# Output JSON Summary (between markers for Python parsing)
# =========================================================================== #
summary_json <- as.list(state)
cat("===KUNLIB_JSON_BEGIN===\n")
cat(toJSON(summary_json, auto_unbox = TRUE, pretty = FALSE))
cat("\n===KUNLIB_JSON_END===\n")
