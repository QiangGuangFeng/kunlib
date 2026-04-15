#!/usr/bin/env Rscript
# generate_demo.r — Generate synthetic aquaculture breeding pedigree
# Produces demo_ped.csv with columns: Ind, Sire, Dam, Year, Sex, Line
# No external dependencies beyond data.table.

suppressPackageStartupMessages(library(data.table))

args <- commandArgs(trailingOnly = TRUE)
parse_arg <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (length(idx) == 0) return(default)
  args[idx + 1]
}

output_dir <- parse_arg("--output", default = ".")
set.seed(2024)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
line_names        <- c("Line_A", "Line_B", "Line_C")
founders_per_line <- 20L   # 10 male + 10 female per line = 60 founders total
n_offspring_gen   <- 5L    # offspring generations (Gen 1-5)
n_families        <- 30L   # families per generation
n_offspring       <- 30L   # offspring per family
n_sires_used      <- 10L   # unique sires per generation (nested design → half-sibs)
n_inbred_fam      <- 8L    # half-sib mating families in Gen 4-5
years             <- 2018L:2023L  # Gen 0 = 2018 .. Gen 5 = 2023

# --------------------------------------------------------------------------- #
# Generation 0: Founders with Line labels
# --------------------------------------------------------------------------- #
founder_list <- list()
for (ln in line_names) {
  for (sx in c("male", "female")) {
    n <- founders_per_line %/% 2L
    tag <- if (sx == "male") "M" else "F"
    ids <- sprintf("F0_%s_%s%02d", ln, tag, seq_len(n))
    founder_list[[length(founder_list) + 1L]] <- data.table(
      Ind  = ids,
      Sire = NA_character_,
      Dam  = NA_character_,
      Year = years[1L],
      Sex  = sx,
      Line = ln
    )
  }
}
all_ped <- rbindlist(founder_list)

# --------------------------------------------------------------------------- #
# Generations 1-5: Offspring with nested sire design
# --------------------------------------------------------------------------- #
dams_per_sire <- n_families %/% n_sires_used  # 3

for (gen in seq_len(n_offspring_gen)) {
  year <- years[gen + 1L]
  prev <- all_ped[Year == years[gen]]
  prev_m <- prev[Sex == "male", Ind]
  prev_f <- prev[Sex == "female", Ind]

  # Select sires and dams from previous generation
  sires <- sample(prev_m, min(n_sires_used, length(prev_m)))
  dams  <- sample(prev_f, min(n_families, length(prev_f)))

  gen_records <- vector("list", n_families)

  for (fam in seq_len(n_families)) {
    # Nested design: each sire mates with `dams_per_sire` dams
    sire_idx <- min(((fam - 1L) %/% dams_per_sire) + 1L, length(sires))
    sire_id  <- sires[sire_idx]
    dam_id   <- dams[min(fam, length(dams))]

    # ---- Inbreeding injection in Gen 4-5 ----
    # Mate half-sibs (share same grandsire) to produce inbred offspring
    if (gen >= 4L && fam <= n_inbred_fam) {
      candidate_sire <- sample(prev_m, 1L)
      grandsire <- all_ped[Ind == candidate_sire, Sire]
      if (!is.na(grandsire) && nchar(grandsire) > 0L) {
        half_sisters <- prev[Sire == grandsire & Sex == "female" &
                             Ind != candidate_sire, Ind]
        if (length(half_sisters) > 0L) {
          sire_id <- candidate_sire
          dam_id  <- sample(half_sisters, 1L)
        }
      }
    }

    ids   <- sprintf("G%d_F%02d_%03d", gen, fam, seq_len(n_offspring))
    sexes <- sample(c("male", "female"), n_offspring, replace = TRUE)

    gen_records[[fam]] <- data.table(
      Ind  = ids,
      Sire = sire_id,
      Dam  = dam_id,
      Year = year,
      Sex  = sexes,
      Line = NA_character_
    )
  }

  all_ped <- rbind(all_ped, rbindlist(gen_records))
}

# --------------------------------------------------------------------------- #
# Write output
# --------------------------------------------------------------------------- #
fwrite(all_ped, file.path(output_dir, "demo_ped.csv"),
       sep = ",", col.names = TRUE, row.names = FALSE, quote = FALSE, na = "NA")

cat(sprintf("Demo pedigree: %d individuals, %d years (%d-%d)\n",
            nrow(all_ped), length(years), min(years), max(years)))
cat(sprintf("Founders: %d (%s)\n",
            sum(is.na(all_ped$Sire)), paste(line_names, collapse = ", ")))
cat(sprintf("Inbred families: %d families targeted in Gen 4-5\n", n_inbred_fam))
