#!/usr/bin/env Rscript
# run_lagm.r — KunLib wrapper for lagm::lagm_plan()
# Called by lagm_mating.py via subprocess.

suppressPackageStartupMessages({
  if (!require(lagm, quietly = TRUE)) {
    if (!require(remotes, quietly = TRUE)) install.packages("remotes", repos = "https://cran.r-project.org")
    remotes::install_github("kzy599/LAGM", subdir = "lagmRcpp")
    library(lagm)
  }
  library(data.table)
})

# --------------------------------------------------------------------------- #
# Helper: build G/D/E relationship matrix from genotype (VanRaden-style)
# --------------------------------------------------------------------------- #
makeGDE <- function(x, type = "D", inv = FALSE) {
  if (!is.matrix(x)) x <- as.matrix(x)

  if (type == "E") {
    M <- x - 1
    E <- 0.5 * ((M %*% t(M)) * (M %*% t(M))) - 0.5 * ((M * M) %*% t(M * M))
    E <- E / (sum(diag(E)) / nrow(E))
    A <- diag(1, nrow(E))
    E <- E * 0.99 + A * 0.01
    if (inv) solve(E) else E
  } else if (type == "D") {
    P <- apply(x, 2, function(col) {
      pi <- sum(col) / (2 * length(col))
      if (pi > 0.5) pi <- 1 - pi
      pi
    })
    W <- apply(x, 2, function(col) {
      pi <- sum(col) / (2 * length(col))
      if (pi > 0.5) {
        pi <- 1 - pi
        AA_bool <- which(col == 0)
        aa_bool <- which(col == 2)
        col[AA_bool] <- 2
        col[aa_bool] <- 0
      }
      aa <- -2 * (pi^2)
      Aa <- 2 * pi * (1 - pi)
      AA <- -2 * ((1 - pi)^2)
      col[which(col == 0)] <- aa
      col[which(col == 1)] <- Aa
      col[which(col == 2)] <- AA
      col
    })
    D <- (W %*% t(W)) / sum((2 * P * (1 - P))^2)
    A <- diag(1, nrow(D))
    D <- D * 0.99 + A * 0.01
    if (inv) solve(D) else D
  } else {
    # type == "G" (default additive)
    P <- apply(x, 2, function(col) {
      pi <- sum(col) / (2 * length(col))
      if (pi > 0.5) pi <- 1 - pi
      pi
    })
    Z <- apply(x, 2, function(col) {
      pi <- sum(col) / (2 * length(col))
      if (pi > 0.5) {
        pi <- 1 - pi
        AA_bool <- which(col == 0)
        aa_bool <- which(col == 2)
        col[AA_bool] <- 2
        col[aa_bool] <- 0
      }
      col <- col - 2 * pi
      col
    })
    G <- (Z %*% t(Z)) / sum(2 * P * (1 - P))
    A <- diag(1, nrow(G))
    G <- G * 0.99 + A * 0.01
    if (inv) solve(G) else G
  }
}

# --------------------------------------------------------------------------- #
# Parse CLI arguments
# --------------------------------------------------------------------------- #
args <- commandArgs(trailingOnly = TRUE)

parse_arg <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (length(idx) == 0) return(default)
  args[idx + 1]
}
parse_flag <- function(flag) {
  flag %in% args
}

id_index_file    <- parse_arg("--id-index-file")
geno_file        <- parse_arg("--geno-file")
ped_file         <- parse_arg("--ped-file", default = "")
workdir          <- parse_arg("--workdir", default = ".")
tables_dir       <- parse_arg("--tables-dir", default = ".")

t_val            <- as.integer(parse_arg("--t", default = "3"))
n_crosses        <- as.integer(parse_arg("--n-crosses", default = "30"))
male_min         <- as.integer(parse_arg("--male-contribution-min", default = "2"))
male_max         <- as.integer(parse_arg("--male-contribution-max", default = "2"))
female_min       <- as.integer(parse_arg("--female-contribution-min", default = "1"))
female_max       <- as.integer(parse_arg("--female-contribution-max", default = "1"))
diversity_mode   <- parse_arg("--diversity-mode", default = "genomic")
use_ped          <- parse_flag("--use-ped")
n_iter           <- as.integer(parse_arg("--n-iter", default = "30000"))
n_pop            <- as.integer(parse_arg("--n-pop", default = "100"))
n_threads        <- as.integer(parse_arg("--n-threads", default = "8"))
swap_prob        <- as.numeric(parse_arg("--swap-prob", default = "0.2"))
init_prob        <- as.numeric(parse_arg("--init-prob", default = "0.8"))
cooling_rate     <- as.numeric(parse_arg("--cooling-rate", default = "0.998"))
stop_window      <- as.integer(parse_arg("--stop-window", default = "2000"))
stop_eps         <- as.numeric(parse_arg("--stop-eps", default = "1e-8"))

# --------------------------------------------------------------------------- #
# Read and validate inputs
# --------------------------------------------------------------------------- #
id_index_dt <- fread(id_index_file)
# Enforce column order: col1=ID, col2=selindex, col3=sex
if (ncol(id_index_dt) < 3) stop("id_index_sex file must have at least 3 columns: ID, selindex, sex")
colnames(id_index_dt)[1:3] <- c("ID", "selindex", "sex")

geno_dt <- fread(geno_file)
# Enforce column order: col1=ID, remaining=SNP markers
colnames(geno_dt)[1] <- "ID"

# Validate sex values
valid_sex <- id_index_dt$sex %in% c("M", "F")
if (!all(valid_sex)) {
  bad <- id_index_dt$ID[!valid_sex]
  stop(paste0("Invalid sex values for IDs: ", paste(head(bad, 5), collapse = ", "),
              ". Sex must be 'M' or 'F'."))
}

male_ids       <- id_index_dt[sex == "M", ID]
female_ids     <- id_index_dt[sex == "F", ID]
candidate_ids  <- id_index_dt$ID
candidate_ebv  <- id_index_dt$selindex

female_min_vec <- rep(female_min, length(female_ids))
female_max_vec <- rep(female_max, length(female_ids))
male_min_vec   <- rep(male_min, length(male_ids))
male_max_vec   <- rep(male_max, length(male_ids))

# Align genotype to id_index order
geno_dt <- geno_dt[match(id_index_dt$ID, geno_dt$ID), ]
if (any(is.na(geno_dt$ID))) {
  stop("Some IDs in id_index_sex are not found in geno file.")
}

# --------------------------------------------------------------------------- #
# Build diversity matrix
# --------------------------------------------------------------------------- #
geno_matrix         <- NULL
relationship_matrix <- NULL

if (diversity_mode != "genomic" && use_ped) {
  # Pedigree-based relationship matrix
  if (ped_file == "" || !file.exists(ped_file)) {
    stop("--ped-file is required when use_ped is TRUE and diversity_mode != 'genomic'")
  }
  if (!require(visPedigree, quietly = TRUE)) {
    stop("R package 'visPedigree' is required for pedigree mode. Install via remotes::install_github('luansheng/visPedigree')")
  }
  ped_dt <- fread(ped_file)
  if (ncol(ped_dt) < 3) stop("ped file must have at least 3 columns: ID, sire, dam")
  colnames(ped_dt)[1:3] <- c("ID", "sire", "dam")
  ped_dt <- visPedigree::tidyped(ped_dt, cand = id_index_dt$ID)
  Amat <- visPedigree::pedmat(ped_dt)
  idx <- match(id_index_dt$ID, colnames(Amat))
  Amat <- Amat[idx, idx]
  diversity_mode      <- "relationship"
  relationship_matrix <- Amat
} else if (diversity_mode != "genomic" && !use_ped) {
  # Genomic relationship matrix (G-matrix)
  gm <- as.matrix(geno_dt[, -1])
  relationship_matrix <- makeGDE(x = gm, type = "G", inv = FALSE)
} else {
  # Genomic mode: pass raw genotypes
  geno_matrix <- as.matrix(geno_dt[, -1])
}

# --------------------------------------------------------------------------- #
# Run lagm_plan
# --------------------------------------------------------------------------- #
mating_plan <- lagm_plan(
  individual_ids         = candidate_ids,
  female_ids             = female_ids,
  male_ids               = male_ids,
  ebv_vector             = as.numeric(candidate_ebv),
  n_crosses              = n_crosses,
  lookahead_generations  = t_val,
  female_min             = female_min_vec,
  female_max             = female_max_vec,
  male_min               = male_min_vec,
  male_max               = male_max_vec,
  diversity_mode         = diversity_mode,
  base_diversity         = 1,
  geno_matrix            = geno_matrix,
  relationship_matrix    = relationship_matrix,
  swap_prob              = swap_prob,
  init_prob              = init_prob,
  cooling_rate           = cooling_rate,
  stop_window            = stop_window,
  stop_eps               = stop_eps,
  n_iter                 = n_iter,
  n_pop                  = n_pop,
  n_threads              = n_threads
)

# --------------------------------------------------------------------------- #
# Write output
# --------------------------------------------------------------------------- #
out_path <- file.path(tables_dir, "mating_plan.csv")
fwrite(mating_plan, file = out_path, col.names = TRUE, row.names = FALSE,
       quote = FALSE, sep = ",", nThread = n_threads)
cat(paste0("Mating plan written to: ", out_path, "\n"))
cat(paste0("Total crosses: ", nrow(mating_plan), "\n"))
