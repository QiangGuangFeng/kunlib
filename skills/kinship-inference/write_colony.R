library(data.table)
library(magrittr)
library(xfun)
source("functions_colony.R")
##### 1K 位点
snp_1K_dt <- fread("./demo/1K位点.txt",header = FALSE)
##### 芯片数据1
gt1_dt <- fread("./demo/ZZ2024G06_off_gt1556.csv.gz")
gt1_1K_dt <- extract_gt(gt1_dt,snp_1K_dt$V1)

#### 样本分型信息
sample_info_dt <- fread("./demo/SampleInfo.csv")
##### 芯片数据2
gt2_dt <- fread("./demo/All.GT_ZZG06_par_tag_55K_213.csv.gz")
gt2_1K_dt <- extract_gt(gt2_dt,snp_1K_dt$V1)

gt_1k_dt <- merge(gt1_1K_dt,gt2_1K_dt[,-c(2,3,4)],by="ID")
setwd("./demo")
### GT2PedMap
GT2PedMap(raw_geno_dt = gt_1k_dt)
### PLINK质控
QC_plink(fileName = "GenoIndPlink")
#### Tidy_gt
ped_dt <- fread("SNP012Plink.ped")
ped_dt <- ped_dt[,-c(2,3,4,5,6)]
tidy_gt_dt <- Tidy_GT(gt.data = ped_dt)
# ##### write colony parameters file
### 子代的基因型 (含靶标个体)
## 如果sample_info_dt含有Class=="Tag"，则说明有靶标个体，子代基因型包含靶标个体和Class=="Offspring"的个体；如果没有，则说明没有靶标个体，子代基因型仅包含Class=="Offspring"的个体
off_names_v <- NULL
if("Tag" %in% unique(sample_info_dt$Class)){
  off_names_v <- c(sample_info_dt[Class=="Tag"]$GenotypeID,sample_info_dt[Class=="Offspring"]$GenotypeID)
} else {
  off_names_v <- sample_info_dt[Class=="Offspring"]$GenotypeID
}
offspring_tidy_gt_dt <- tidy_gt_dt[V1 %in% off_names_v]

### 亲本的基因型
## 如果sample_info_dt含有Class=="Sire"，则说明有父本，父本基因型包含Class=="Sire"的个体；如果没有，则说明没有父本，父本基因型为空
## 父本
male_tidy_gt_dt <- NULL
if("Sire" %in% unique(sample_info_dt$Class)){ 
  male_tidy_gt_dt <- tidy_gt_dt[V1 %in% sample_info_dt[Class=="Sire"]$GenotypeID]
}
## 母本
## 如果sample_info_dt含有Class=="Dam"，则说明有母本，母本基因型包含Class=="Dam"的个体；如果没有，则说明没有母本，母本基因型为空
female_tidy_gt_dt <- NULL
if("Dam" %in% unique(sample_info_dt$Class)){
  female_tidy_gt_dt <- tidy_gt_dt[V1 %in% sample_info_dt[Class=="Dam"]$GenotypeID]
}
########## write colony.dat
snp_names <- fread("SNP012Plink.snplist",header = FALSE)$V1
sink(file = "colony.dat")
## 将下面的cat内容修改成类似94到100行的内容，参数值根据实际情况修改
project_name <- "ZZG06PedRebuild"
output_file_name <- "ZZG06PedRebuild"
off_ind_num <- nrow(offspring_tidy_gt_dt) #子代个体数量
loci_num <- length(snp_names) #位点数量
seed_num <- 1230 #随机数种子
update_allele_freq <- 0 #是否更新基因频率，0=不更新，1=更新
species_type <- 2 #物种类型，2=二性，1=单性
inbreeding <- 0 #是否存在近交，0=不存在，1=存在
ploidy_type <- 0 #倍性类型，0=二倍体，1=单倍体
mating_system <- "1 1" #交配系统，0=多配，1=单配，格式为"父本交配系统 母本交配系统"
clone_inference <- 0 #是否进行克隆推断，0=不进行，1=进行
scale_full_sibship <- 1 #是否缩放全同胞关系，0=不缩放，1=缩放
sibship_prior <- 0 #同胞关系先验，0=无，1=弱，2=中等，3=强，4=Ne的最优同胞关系先验
pop_allele_freq <- 0 #是否已知群体基因频率，0=未知，1=已知
run_num <- 1 #运行次数
run_length <- 2 #运行长度，1=短，2=中等，3=长，4=非常长
monitor_method <- 1 #监控方法，0=迭代次数，1=时间（秒）
monitor_interval <- 1 #监控间隔，单位为迭代次数或秒
system_version <- 0 #系统版本，0=DOS，1=Windows
inference_method <- 1 #推断方法，0=对数似然分数
precision_level <- 1 #精度水平，0=低，1=中，2=高，3=非常高

cat(glue::glue("{project_name}     ! Project name
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
##### ErrorRate
marker_type_v <- 0  # Marker标记类型，0=SNP、SSR; 1=其他标记：RAPD、AFLP等
marker_type <- rep(marker_type_v,length(snp_names))
dropout_rate_v <- 0.001 #等位基因丢失率
dropout_rate <- rep(dropout_rate_v,length(snp_names))
error_rate_v <- 0.05 # 其他错误率（基因分型错误率）
error_rate <- rep(error_rate_v,length(snp_names))

errorRate_dt <- data.table(snp_names,marker_type,dropout_rate,error_rate)
fwrite(t(errorRate_dt),"colony.dat",append = T,quote = F,sep = " ",row.names = F,col.names = F)
###### 写入后代基因型
fwrite(offspring_tidy_gt_dt,"colony.dat",quote = F,sep = " ",append = T,row.names = F,col.names = F)
sink(file = "colony.dat",append = T)
male_cand_prob <- 0.5 #父本候选个体包含率
female_cand_prob <- 0.5 #母本候选个体包含率
male_cand_num <- nrow(male_tidy_gt_dt) #父本候选个体数量
female_cand_num <- nrow(female_tidy_gt_dt) #母本候选个体数量

cat(glue::glue('{male_cand_prob} {female_cand_prob} !probabilities that the father and mother of an offspring are included in candidates
{male_cand_num} {female_cand_num} !Numbers of candidate males and females
'))
sink()
#### 写入父本基因型,如果没有父本，则不写入任何父本基因型
if(!is.null(male_tidy_gt_dt)){ 
  fwrite(male_tidy_gt_dt,"colony.dat",quote = F,sep = " ",append = T,row.names = F,col.names = F)
}
#### 写入母本基因型
if(!is.null(female_tidy_gt_dt)){
  fwrite(female_tidy_gt_dt,"colony.dat",quote = F,sep = " ",append = T,row.names = F,col.names = F)
}
sink(file = "colony.dat",append = T)
## 以下不要修改
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
