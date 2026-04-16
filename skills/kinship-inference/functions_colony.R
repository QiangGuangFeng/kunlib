extract_gt <- function(gt.data,snp.name){
  gt.data=gt.data[ID %in% snp.name]
  return(gt.data)
}

GT2PedMap <- function(raw_geno_dt,missing_gt_s="NA",snp_loci_col_header_s="ID",sample_begin_pos_s=5,OutputName="GenoIndPlink"){
  # raw_geno_dt <- fread(
  #   input = paste("./", fileName, sep = ""),
  #   sep = ",",
  #   header = TRUE,
  #   stringsAsFactors = FALSE,
  #   na.strings = missing_gt_s,
  #   data.table = TRUE
  # )
  # 获取分型文件中的行数, 大于等于SNP位点数
  raw_row_num_s <- nrow(raw_geno_dt)
  # 获取分型文件中的列数, 大于分型个体数
  raw_col_num_s <- ncol(raw_geno_dt)
  # 样本数
  sample_num_s <- raw_col_num_s - sample_begin_pos_s + 1
  # 位点数
  snp_loci_num_s <- raw_row_num_s
  # 获取SNP位点的名称
  if (snp_loci_col_header_s %chin%  colnames(raw_geno_dt)) {
    snp_loci_names_v <- raw_geno_dt[[snp_loci_col_header_s]]
  } else {
    stop(paste0("分型文件中未发现SNP位点列名称", snp_loci_col_header_s))
  }
  # 获取样本的名称
  sample_names_v <-
    colnames(raw_geno_dt)[(raw_col_num_s - sample_num_s + 1):raw_col_num_s]
  # 利用data.table函数transpose进行行列转置
  # 转置后,pure_geno_dt仅包括分型信息,每一行为一尾个体snp_loci_num_s个位点的分型信息
  pure_geno_dt <-
    data.table::transpose(raw_geno_dt[(raw_row_num_s - snp_loci_num_s + 1):raw_row_num_s,
                                      ..sample_names_v])
  # 设置样本名称和样本名称
  rownames(pure_geno_dt) <- sample_names_v
  colnames(pure_geno_dt) <- snp_loci_names_v
  # 把2个以上字符的基因型设置为NA
  setGT2CharasNA = function(DT) {
    for (j in seq_len(ncol(DT)))
      set(DT, which(nchar(DT[[j]]) > 2), j, NA)
  }
  setGT2CharasNA(pure_geno_dt)
  # 生成Plink软件需要的ped文件。
  # plink ped文件前六列**
  # * 家系编号 #可以用--no-fid不输入该列
  # * 个体编号
  # * 父本编号 #可以用--no-parents不输入该列
  # * 母本编号 #可以用--no-parents不输入该列
  # * 性别   #可以用--no-sex不设置该列  1=male,2=female,其他数字代表性别未知
  # * 表型值 ##可以用--no-pheno不输入该列
  # * 从第七列开始，就是snp分型信息
  # 生成的ped文件中,只包括第2列和其SNP位点分型信息.
  # ped不需要列表头。因此设置col.names=FALSE。缺失基因型需要填充为00.
  # plink 会自动识别譬如 AG GC等格式,因此不需要单独分开.
  fwrite(
    x = pure_geno_dt,
    file = paste0("./", OutputName,".ped"),
    sep = " ",
    na = "00",
    row.names = TRUE,
    col.names = FALSE,
    quote = FALSE
  )
  # 生成plink需要的map文件信息
  # 主要包括4列:
  # * 染色体编号;
  # * 位点名称;
  # * 遗传距离;
  # * 基因组上碱基对位置。
  # 因为目前还没有基因组测序，除了SNP位点名称信息外，其他信息缺失.
  # 染色体编号设置为1，其他信息都缺失，设置为0。
  SNP_dt <- data.table(SNP=snp_loci_names_v)
  SNP_dt[,c("Chrom1","Chrom2","Position"):=tstrsplit(SNP,"_",keep = c(1,2,3))]
  SNP_dt[,Chrom:=paste(Chrom1,Chrom2,sep = "_")]
  chromosome_v <- SNP_dt$Chrom
  snp_ID_v <- snp_loci_names_v
  distance_v <- rep(0, snp_loci_num_s)
  position_v <- SNP_dt$Position
  snp_map_dt <-
    data.table(chromosome_v, snp_ID_v, distance_v, position_v)
  fwrite(
    x = snp_map_dt,
    file = paste0("./", OutputName,".map"),
    sep = " ",
    row.names = FALSE,
    col.names = FALSE,
    quote = FALSE
  )
}

Tidy_GT <- function(gt.data){
  gt_dt=gt.data[,colnames(gt.data)[-1]:=lapply(.SD, function(x){
    stringi::stri_replace_all_fixed(x,c("A","C","G","T"),c(1,2,3,4),vectorize_all = F)
  }),.SDcols=colnames(gt.data)[-1]]
  return(gt_dt)
}

QC_plink <- function(fileName="GenoIndPlink",MAF_s=0.05,animal_call_rate_s=0.80,geno_call_rate_s=0.90){
  # --maf 0.05 最小等位基因频率小于0.01的标记将被删除；
  # --geno 0.10 对于每个标记，如果在样本中的丢失率超过0.1，删除该标记；
  # --mind 0.10 对于每个个体，如果有超过10%的标记不能检出，删除该个体;
  # --snps-only 移出InDel，仅保留转换和颠换等形式SNP位点
  # --recode 12 将等位基因型转换为1 2 形式，缺失等位基因用0表示;
  # --recode A 转换为基因含量0 1 2形式，缺失用NA表示；
  # --output-missing-genotype 5 设置缺失值为5;
  #    对于--recode A, 缺失值固定为NA. --output-missing-genotype不起作用，
  #    作者给出的解释是--recode A转换后，有一个值就会是0，
  #    如果用户不小心设置输出缺失基因型为0，那么就分不清那个是哪个了。
  #    因此固定设置为NA.
  # --make-rel square 计算个体间的亲缘关系并以方阵形式保存;
  # --pca 提取标准化的方差亲缘关系矩阵的20个主成分
  # --ibc 计算个体的三种近交系数，貌似第二种比较靠谱.
  # --out 定义输出文件前缀尾SNP012Plink
  common_plink_parameters <- paste(
    "--mind",
    (1 - animal_call_rate_s),
    "--maf",
    MAF_s,
    "--geno",
    (1 - geno_call_rate_s),
    "--snps-only",
    "--freq",
    "--recode",
    "--allow-extra-chr",
    "--make-rel square gz",
    "--ibc",
    "--distance-matrix",
    "--pca",
    "--write-snplist",
    "--out",
    "SNP012Plink",
    sep = " "
  )
  # plink质控参数
  # --ped --map 分别设置输入的ped和map文件;
  # --no-parents，ped文件中不包括父本和母本编号列
  # --no-sex，ped文件中不包括性别列
  # --no-pheno，ped文件中不包括表型值列
  # --no-fid，ped文件中不包括家系编号列
  # 设置质控参数
  plink_args_v <-
    paste(
      "--ped",
      paste0(fileName,".ped"),
      "--map",
      paste0(fileName,".map"),
      "--no-parents",
      "--no-sex",
      "--no-pheno",
      "--no-fid",
      common_plink_parameters,
      sep = " "
    )
  if (is_windows()) {
    system2("plink64.exe",
            args = plink_args_v,
            stdout = "Plink.log",
            wait = TRUE)
  }
  
  if (is_linux()) {
    system2("plink",
            args = plink_args_v,
            stdout = "Plink.log",
            wait = TRUE)
  }
}
