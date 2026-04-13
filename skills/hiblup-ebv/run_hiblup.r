#!/usr/bin/env Rscript
# run_hiblup.r — Run GBLUP analysis (VanRaden G-matrix + MME solver)
# Usage: Rscript run_hiblup.r <input_dir> <output_dir> <trait_pos>

suppressPackageStartupMessages(library(data.table))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: Rscript run_hiblup.r <input_dir> <output_dir> <trait_pos>")
}

input_dir  <- args[1]
output_dir <- args[2]
trait_pos  <- as.integer(args[3])

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# ---------- Read inputs ----------
phe    <- fread(file.path(input_dir, "phe.csv"))
geno   <- fread(file.path(input_dir, "geno.csv"))
sel_id <- fread(file.path(input_dir, "sel_id.csv"))
ref_id <- fread(file.path(input_dir, "ref_id.csv"))

cat("Phenotype dimensions:", nrow(phe), "x", ncol(phe), "\n")
cat("Genotype dimensions:", nrow(geno), "x", ncol(geno), "\n")
cat("Reference animals:", nrow(ref_id), "\n")
cat("Selection candidates:", nrow(sel_id), "\n")
cat("Trait position:", trait_pos, "\n")

# ---------- Build G matrix (VanRaden method 1) ----------
ids   <- geno[[1]]
M     <- as.matrix(geno[, -1, with = FALSE])
p     <- colMeans(M) / 2
P     <- 2 * (rep(1, nrow(M)) %o% p)
Z     <- M - P
denom <- 2 * sum(p * (1 - p))
G     <- (Z %*% t(Z)) / denom
rownames(G) <- ids
colnames(G) <- ids

# ---------- Solve Mixed Model Equations (GBLUP) ----------
# y = Xb + Zu + e
# Henderson's MME:
#   [X'X         X'Z             ] [b] = [X'y]
#   [Z'X    Z'Z + G^{-1}*lambda ] [u]   [Z'y]
# where lambda = sigma_e^2 / sigma_u^2

trait_col <- names(phe)[trait_pos]
y <- phe[[trait_col]]
names(y) <- phe[[1]]

# Match IDs
common_ids <- intersect(names(y), ids)
y <- y[common_ids]
G_sub <- G[common_ids, common_ids]

n <- length(y)
X <- matrix(1, n, 1)   # intercept only
Z <- diag(n)

# Assume heritability h2 = 0.3 for lambda
h2     <- 0.3
lambda <- (1 - h2) / h2

G_inv <- solve(G_sub + diag(1e-4, n))   # regularised inverse

# MME
LHS <- rbind(
  cbind(t(X) %*% X,          t(X) %*% Z),
  cbind(t(Z) %*% X, t(Z) %*% Z + G_inv * lambda)
)
RHS <- c(t(X) %*% y, t(Z) %*% y)

sol <- solve(LHS, RHS)
mu  <- sol[1]
ebv <- sol[2:(n + 1)]
names(ebv) <- common_ids

# ---------- Write outputs ----------
phe_ebv <- data.table(ID = common_ids, EBV = round(ebv, 4))
fwrite(phe_ebv, file.path(output_dir, "phe_ebv.csv"))

sel_matched <- phe_ebv[ID %in% sel_id[[1]]]
fwrite(sel_matched, file.path(output_dir, "sel_ebv.csv"))

ref_matched <- phe_ebv[ID %in% ref_id[[1]]]
fwrite(ref_matched, file.path(output_dir, "ref_ebv.csv"))

cat("EBV estimation complete.\n")
cat("  phe_ebv.csv:", nrow(phe_ebv), "records\n")
cat("  sel_ebv.csv:", nrow(sel_matched), "records\n")
cat("  ref_ebv.csv:", nrow(ref_matched), "records\n")
