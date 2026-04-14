library(AlphaSimR)
library(data.table)

makeped = function(z){
  z[!(z == 0 | z == 1 | z == 2)] <- -9
  
  z[z == 2] <- 22
  z[z == 1] <- 12
  z[z == 0] <- 11

  dt <- as.data.table(z, keep.rownames = "ID")
  return(dt)
  }

founderPop = quickHaplo(nInd=100, nChr=5, segSites=500)
SP <- SimParam$new(founderPop)

SP$addTraitA(nQtlPerChr = 100,
              mean=c(0,0),var = c(1,1),
              corA = matrix(c(1,0.3,0.3,1),nrow = 2))

SP$setVarE(h2 = c(0.3,0.3)) # 0.17 0.25 in the range of heritability for growth, meat yield, survival, etc
SP$addSnpChip(nSnpPerChr = 400) # all non-QTL SNPs saved from simulation
SP$setSexes("yes_sys") # at the time of breeding, all individuals will only be one sex

pop_founder = newPop(founderPop, simParam=SP)


nDam = 20
nSire = 10
nCrosses = 20
nProgenyPerCross = 10
nProgeny = nProgenyPerCross
pop <- selectCross(pop_founder,
                   nFemale = nDam,nMale = nSire,
                   nCrosses = nCrosses,nProgeny = nProgenyPerCross,
                   use = "rand",
                   simParam = SP)

id_index_sex = data.table(ID = pop@id,selindex = pop@pheno[,1],sex=pop@sex)
fwrite(id_index_sex,file = "id_index_sex.csv",sep = ",",col.names = TRUE,row.names = FALSE,quote = FALSE,na = "NA")

ped = data.table(ID = pop@id, sire = pop@father, dam = pop@mother)
fwrite(ped,file = "ped.csv",sep = ",",col.names = TRUE,row.names = FALSE,quote = FALSE,na = "NA")

geno_mat = pullSnpGeno(pop)
geno_dt <- as.data.table(geno_mat, keep.rownames = "ID")
fwrite(geno_dt,file="geno.csv",col.names = TRUE,row.names = FALSE, quote = FALSE,sep = ",",nThread = 8)
