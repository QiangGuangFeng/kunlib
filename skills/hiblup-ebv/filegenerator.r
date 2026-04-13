#!/usr/bin/env Rscript
# filegenerator.r — Generate synthetic demo data for hiblup-ebv skill
# Usage: Rscript filegenerator.r <output_dir>

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript filegenerator.r <output_dir>")
}

output_dir <- args[1]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

set.seed(42)

n_animals  <- 100
n_markers  <- 50
n_ref      <- 70
n_sel      <- 30

# Generate IDs
ids <- paste0("ANIMAL_", sprintf("%03d", 1:n_animals))

# Phenotype: ID + Trait1
trait1 <- round(rnorm(n_animals, mean = 100, sd = 15), 2)
phe <- data.frame(ID = ids, Trait1 = trait1)
write.csv(phe, file.path(output_dir, "phe.csv"), row.names = FALSE)

# Genotype: ID + marker columns (0/1/2)
geno_mat <- matrix(sample(0:2, n_animals * n_markers, replace = TRUE),
                   nrow = n_animals, ncol = n_markers)
colnames(geno_mat) <- paste0("SNP_", 1:n_markers)
geno <- data.frame(ID = ids, geno_mat)
write.csv(geno, file.path(output_dir, "geno.csv"), row.names = FALSE)

# Reference IDs (first n_ref)
ref_ids <- data.frame(ID = ids[1:n_ref])
write.csv(ref_ids, file.path(output_dir, "ref_id.csv"), row.names = FALSE)

# Selection IDs (last n_sel)
sel_ids <- data.frame(ID = ids[(n_animals - n_sel + 1):n_animals])
write.csv(sel_ids, file.path(output_dir, "sel_id.csv"), row.names = FALSE)

cat("Demo data generated in:", output_dir, "\n")
