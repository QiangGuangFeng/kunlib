#!/usr/bin/env Rscript
# run_kinship.R — KunLib CLI wrapper for kinship-inference pipeline
# Called by kinship_inference.py via subprocess
#
# Usage:
#   Rscript --vanilla run_kinship.R \
#     --snp-files "file1.csv.gz,file2.csv.gz" \
#     --snp-list-file 1K位点.txt \
#     --sample-info-file SampleInfo.csv \
#     --input-dir /path/to/input \
#     --work-dir /path/to/work \
#     --tables-dir /path/to/tables \
#     --project-name MyProject \
#     --output-file-name MyProject \
#     --seed 1234 \
#     --update-allele-freq 0 \
#     --species-type 2 \
#     --inbreeding 0 \
#     --ploidy-type 0 \
#     --mating-system "0 0" \
#     --clone-inference 0 \
#     --scale-full-sibship 1 \
#     --sibship-prior 0 \
#     --pop-allele-freq 0 \
#     --run-num 1 \
#     --run-length 2 \
#     --monitor-method 1 \
#     --monitor-interval 1000 \
#     --system-version 0 \
#     --inference-method 1 \
#     --precision-level 2 \
#     --male-cand-prob 0.5 \
#     --female-cand-prob 0.5 \
#     --marker-type 0 \
#     --dropout-rate 0.001 \
#     --error-rate 0.05

suppressPackageStartupMessages({
  library(data.table)
  library(magrittr)
  library(glue)
  library(stringi)
})

# ---- Parse arguments ----
args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (length(idx) == 0) return(default)
  return(args[idx + 1])
}

input_dir         <- get_arg("--input-dir", ".")
work_dir          <- get_arg("--work-dir", ".")
tables_dir        <- get_arg("--tables-dir", ".")
snp_files_str     <- get_arg("--snp-files", "")
snp_list_file     <- get_arg("--snp-list-file", "1K位点.txt")
sample_info_file  <- get_arg("--sample-info-file", "SampleInfo.csv")
project_name      <- get_arg("--project-name", "KinshipInference")
output_file_name  <- get_arg("--output-file-name", "KinshipInference")
seed_num          <- as.integer(get_arg("--seed", "1234"))
update_allele_freq <- as.integer(get_arg("--update-allele-freq", "0"))
species_type      <- as.integer(get_arg("--species-type", "2"))
inbreeding        <- as.integer(get_arg("--inbreeding", "0"))
ploidy_type       <- as.integer(get_arg("--ploidy-type", "0"))
mating_system     <- get_arg("--mating-system", "0 0")
clone_inference   <- as.integer(get_arg("--clone-inference", "0"))
scale_full_sibship <- as.integer(get_arg("--scale-full-sibship", "1"))
sibship_prior     <- as.integer(get_arg("--sibship-prior", "0"))
pop_allele_freq   <- as.integer(get_arg("--pop-allele-freq", "0"))
run_num           <- as.integer(get_arg("--run-num", "1"))
run_length        <- as.integer(get_arg("--run-length", "2"))
monitor_method    <- as.integer(get_arg("--monitor-method", "1"))
monitor_interval  <- as.integer(get_arg("--monitor-interval", "1000"))
system_version    <- as.integer(get_arg("--system-version", "0"))
inference_method  <- as.integer(get_arg("--inference-method", "1"))
precision_level   <- as.integer(get_arg("--precision-level", "2"))
male_cand_prob    <- as.numeric(get_arg("--male-cand-prob", "0.5"))
female_cand_prob  <- as.numeric(get_arg("--female-cand-prob", "0.5"))
marker_type_v     <- as.integer(get_arg("--marker-type", "0"))
dropout_rate_v    <- as.numeric(get_arg("--dropout-rate", "0.001"))
error_rate_v      <- as.numeric(get_arg("--error-rate", "0.05"))

# ---- Source helper functions ----
# Reliably determine script directory when called via Rscript
initial_args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", initial_args, value = TRUE)
if (length(file_arg) > 0) {
  script_dir <- dirname(normalizePath(sub("^--file=", "", file_arg[1])))
} else {
  script_dir <- dirname(normalizePath(sys.frame(1)$ofile %||% "."))
}
source(file.path(script_dir, "functions_colony.R"))

# ---- Read SNP list ----
snp_list_path <- file.path(input_dir, snp_list_file)
snp_1K_dt <- fread(snp_list_path, header = FALSE)
message(sprintf("[kinship-inference] Read %d target SNPs from %s", nrow(snp_1K_dt), snp_list_file))

# ---- Read and merge SNP chip files ----
snp_files <- trimws(unlist(strsplit(snp_files_str, ",")))
snp_files <- snp_files[nchar(snp_files) > 0]

if (length(snp_files) == 0) {
  stop("[kinship-inference] No SNP chip files provided via --snp-files")
}

message(sprintf("[kinship-inference] Processing %d SNP chip file(s)", length(snp_files)))

# Read and extract target SNPs from each chip file
gt_list <- list()
for (i in seq_along(snp_files)) {
  fpath <- file.path(input_dir, snp_files[i])
  message(sprintf("[kinship-inference] Reading chip file %d: %s", i, snp_files[i]))
  gt_raw <- fread(fpath)
  gt_extracted <- extract_gt(gt_raw, snp_1K_dt$V1)
  gt_list[[i]] <- gt_extracted
  message(sprintf("[kinship-inference]   -> %d SNPs x %d samples extracted", nrow(gt_extracted), ncol(gt_extracted) - 4))
}

# Merge chip files: first file is base, subsequent files merge by ID (dropping chrom/position/ref columns)
gt_merged <- gt_list[[1]]
if (length(gt_list) > 1) {
  for (i in 2:length(gt_list)) {
    gt_merged <- merge(gt_merged, gt_list[[i]][, -c(2, 3, 4)], by = "ID")
  }
}
message(sprintf("[kinship-inference] Merged genotype: %d SNPs x %d samples", nrow(gt_merged), ncol(gt_merged) - 4))

# ---- Read sample info ----
sample_info_path <- file.path(input_dir, sample_info_file)
sample_info_dt <- fread(sample_info_path)
message(sprintf("[kinship-inference] Sample info: %d records", nrow(sample_info_dt)))
for (cls in unique(sample_info_dt$Class)) {
  message(sprintf("[kinship-inference]   Class=%s: %d", cls, nrow(sample_info_dt[Class == cls])))
}

# ---- Convert to PLINK ped/map (in work_dir) ----
old_wd <- getwd()
setwd(work_dir)
on.exit(setwd(old_wd), add = TRUE)

GT2PedMap(raw_geno_dt = gt_merged)
message("[kinship-inference] PLINK ped/map files generated")

# ---- PLINK QC ----
QC_plink(fileName = "GenoIndPlink")
message("[kinship-inference] PLINK QC completed")

# ---- Tidy genotype ----
ped_dt <- fread("SNP012Plink.ped")
ped_dt <- ped_dt[, -c(2, 3, 4, 5, 6)]
tidy_gt_dt <- Tidy_GT(gt.data = ped_dt)
message(sprintf("[kinship-inference] Tidy genotype: %d individuals x %d loci", nrow(tidy_gt_dt), ncol(tidy_gt_dt) - 1))

# ---- Classify individuals by SampleInfo ----
# Offspring = Tag + Offspring (if Tag exists) or just Offspring
off_names_v <- NULL
if ("Tag" %in% unique(sample_info_dt$Class)) {
  off_names_v <- c(
    sample_info_dt[Class == "Tag"]$GenotypeID,
    sample_info_dt[Class == "Offspring"]$GenotypeID
  )
} else {
  off_names_v <- sample_info_dt[Class == "Offspring"]$GenotypeID
}
offspring_tidy_gt_dt <- tidy_gt_dt[V1 %in% off_names_v]

# Sires
male_tidy_gt_dt <- NULL
if ("Sire" %in% unique(sample_info_dt$Class)) {
  male_tidy_gt_dt <- tidy_gt_dt[V1 %in% sample_info_dt[Class == "Sire"]$GenotypeID]
}

# Dams
female_tidy_gt_dt <- NULL
if ("Dam" %in% unique(sample_info_dt$Class)) {
  female_tidy_gt_dt <- tidy_gt_dt[V1 %in% sample_info_dt[Class == "Dam"]$GenotypeID]
}

message(sprintf("[kinship-inference] Offspring: %d, Sires: %d, Dams: %d",
                nrow(offspring_tidy_gt_dt),
                if (!is.null(male_tidy_gt_dt)) nrow(male_tidy_gt_dt) else 0,
                if (!is.null(female_tidy_gt_dt)) nrow(female_tidy_gt_dt) else 0))

# ---- Write colony.dat ----
snp_names <- fread("SNP012Plink.snplist", header = FALSE)$V1
off_ind_num <- nrow(offspring_tidy_gt_dt)
loci_num <- length(snp_names)

colony_dat_path <- file.path(work_dir, "colony.dat")

sink(file = colony_dat_path)
cat(glue("{project_name}     ! Project name
{output_file_name}     ! Output file name
{off_ind_num}       ! Number of offspring in the sample
{loci_num}      ! Number of loci
{seed_num}      ! Seed for random number generator
{update_allele_freq}         ! 0/1=Not updating/updating allele
{species_type}         ! 2/1=Dioecious/Monoecious species
{inbreeding}         ! 0/1=Inbreeding absent/present
{ploidy_type}         ! 0/1=Diploid species/HaploDiploid species
{mating_system}      ! 0/1=Polygamy/Monogamy for males & females
{clone_inference}         ! 0/1 = Clone inference = No/Yes
{scale_full_sibship}         ! 0/1=Scale full sibship=No/Yes
{sibship_prior}         ! 0/1/2/3/4=No/Weak/Medium/Strong sibship prior; 4=Optimal sibship prior for Ne
{pop_allele_freq}         ! 0/1=Unknown/Known population allele frequency
{run_num}         ! Number of runs
{run_length}         ! 1/2/3/4 = Short/Medium/Long/VeryLong run
{monitor_method}         ! 0/1=Monitor method by Iterate#/Time in second
{monitor_interval}         ! Monitor interval in Iterate# / in seconds
{system_version}         ! 0/1=DOS/Windows version
{inference_method}         ! 0/1/2=Pair-Likelihood-Score(PLS)/Full-Likelihood(FL)/FL-PLS-combined(FPLS) method
{precision_level}         ! 0/1/2/3=Low/Medium/High/VeryHigh precision
"))
cat("\n")
sink()

# ErrorRate block
marker_type <- rep(marker_type_v, length(snp_names))
dropout_rate <- rep(dropout_rate_v, length(snp_names))
error_rate <- rep(error_rate_v, length(snp_names))
errorRate_dt <- data.table(snp_names, marker_type, dropout_rate, error_rate)
fwrite(t(errorRate_dt), colony_dat_path, append = TRUE, quote = FALSE, sep = " ", row.names = FALSE, col.names = FALSE)

# Write offspring genotype
fwrite(offspring_tidy_gt_dt, colony_dat_path, quote = FALSE, sep = " ", append = TRUE, row.names = FALSE, col.names = FALSE)

# Candidate probabilities and counts
male_cand_num <- if (!is.null(male_tidy_gt_dt)) nrow(male_tidy_gt_dt) else 0
female_cand_num <- if (!is.null(female_tidy_gt_dt)) nrow(female_tidy_gt_dt) else 0

sink(file = colony_dat_path, append = TRUE)
cat(glue("{male_cand_prob} {female_cand_prob} !probabilities that the father and mother of an offspring are included in candidates
{male_cand_num} {female_cand_num} !Numbers of candidate males and females
"))
sink()

# Write sire genotype
if (!is.null(male_tidy_gt_dt)) {
  fwrite(male_tidy_gt_dt, colony_dat_path, quote = FALSE, sep = " ", append = TRUE, row.names = FALSE, col.names = FALSE)
}

# Write dam genotype
if (!is.null(female_tidy_gt_dt)) {
  fwrite(female_tidy_gt_dt, colony_dat_path, quote = FALSE, sep = " ", append = TRUE, row.names = FALSE, col.names = FALSE)
}

# Trailing COLONY configuration (known pairs etc.)
sink(file = colony_dat_path, append = TRUE)
cat(
"
0  0

0  0

0

0

0

0

0

0
")
sink()

message("[kinship-inference] colony.dat written successfully")

# ---- Copy key output files to tables_dir ----
files_to_copy <- c("colony.dat", "SNP012Plink.snplist", "Plink.log")
for (f in files_to_copy) {
  src <- file.path(work_dir, f)
  if (file.exists(src)) {
    file.copy(src, file.path(tables_dir, f), overwrite = TRUE)
  }
}

# Also copy QC output files
qc_files <- list.files(work_dir, pattern = "^SNP012Plink\\.", full.names = TRUE)
for (f in qc_files) {
  file.copy(f, file.path(tables_dir, basename(f)), overwrite = TRUE)
}

# Write a summary JSON-like file for Python to read
summary_path <- file.path(work_dir, "pipeline_summary.csv")
summary_dt <- data.table(
  key = c("n_target_snps", "n_snp_chips", "n_samples_merged",
          "n_offspring", "n_sires", "n_dams", "n_loci_after_qc",
          "project_name"),
  value = c(nrow(snp_1K_dt), length(snp_files), ncol(gt_merged) - 4,
            nrow(offspring_tidy_gt_dt),
            if (!is.null(male_tidy_gt_dt)) nrow(male_tidy_gt_dt) else 0,
            if (!is.null(female_tidy_gt_dt)) nrow(female_tidy_gt_dt) else 0,
            loci_num,
            project_name)
)
fwrite(summary_dt, summary_path)
message("[kinship-inference] Pipeline summary written to pipeline_summary.csv")

message("[kinship-inference] R pipeline completed successfully")
