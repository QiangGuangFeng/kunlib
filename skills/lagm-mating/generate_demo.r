#!/usr/bin/env Rscript
# generate_demo.r — Generate synthetic demo data for lagm-mating skill.
# Produces id_index_sex.csv, geno.csv, and ped.csv using AlphaSimR.

suppressPackageStartupMessages({
  library(AlphaSimR)
  library(data.table)
})

args <- commandArgs(trailingOnly = TRUE)
parse_arg <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (length(idx) == 0) return(default)
  args[idx + 1]
}

output_dir <- parse_arg("--output", default = ".")

# Create founder population
founderPop <- quickHaplo(nInd = 100, nChr = 5, segSites = 500)
SP <- SimParam$new(founderPop)

SP$addTraitA(
  nQtlPerChr = 100,
  mean = c(0, 0),
  var = c(1, 1),
  corA = matrix(c(1, 0.3, 0.3, 1), nrow = 2)
)
SP$setVarE(h2 = c(0.3, 0.3))
SP$addSnpChip(nSnpPerChr = 400)
SP$setSexes("yes_sys")

pop_founder <- newPop(founderPop, simParam = SP)

nDam <- 20
nSire <- 10
nCrosses <- 20
nProgenyPerCross <- 10

pop <- selectCross(
  pop_founder,
  nFemale = nDam, nMale = nSire,
  nCrosses = nCrosses, nProgeny = nProgenyPerCross,
  use = "rand",
  simParam = SP
)

# Write id_index_sex.csv
id_index_sex <- data.table(
  ID = pop@id,
  selindex = pop@pheno[, 1],
  sex = pop@sex
)
fwrite(id_index_sex, file = file.path(output_dir, "id_index_sex.csv"),
       sep = ",", col.names = TRUE, row.names = FALSE, quote = FALSE, na = "NA")

# Write ped.csv
ped <- data.table(ID = pop@id, sire = pop@father, dam = pop@mother)
fwrite(ped, file = file.path(output_dir, "ped.csv"),
       sep = ",", col.names = TRUE, row.names = FALSE, quote = FALSE, na = "NA")

# Write geno.csv
geno_mat <- pullSnpGeno(pop)
geno_dt <- as.data.table(geno_mat, keep.rownames = "ID")
fwrite(geno_dt, file = file.path(output_dir, "geno.csv"),
       col.names = TRUE, row.names = FALSE, quote = FALSE, sep = ",", nThread = 8)

cat("Demo data generated successfully.\n")
