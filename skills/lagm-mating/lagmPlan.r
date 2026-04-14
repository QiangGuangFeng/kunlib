if (!require(lagm)) {
  remotes::install_github("kzy599/LAGM", subdir = "lagmRcpp")
  library(lagm)
}
library(data.table)
library(visPedigree)
makeGDE = function(x,type = "D",inv = FALSE){
  
  if(!is.matrix(x)) x <- as.matrix(x)
  
  if(type=="E"){

      M = x - 1
      
      E <- 0.5 * ((M %*% t(M)) * (M %*% t(M))) - 0.5 * ((M * M) %*% t(M * M))
      
      E <- E / (sum(diag(E)) / nrow(E))
      
      A = diag(1,nrow(E))
      
      E = E * 0.99 + A * 0.01

      
      if(inv) inverse <- solve(E) else inverse <- E

  }else if(type == "D"){

      P = apply(x,2,function(col){
      
        pi = sum(col)/(2*length(col))
      
        if(pi>0.5) pi = 1-pi
      
        return(pi)
      
      })

      W = apply(x,2,function(col){
          
          pi = sum(col)/(2*length(col))
          
          if(pi>0.5){
          
            pi = 1-pi
          
            AA_bool = which(col == 0)
          
            aa_bool = which(col == 2)
          
            col[AA_bool] = 2
          
            col[aa_bool] = 0
          
          }
          
          aa = -2 * (pi^2)
          
          Aa = 2 * pi * (1-pi)
          
          AA = -2 * ((1-pi)^2)
          
          aa_bool = which(col == 0)
          
          Aa_bool = which(col == 1)
          
          AA_bool = which(col == 2)
          
          col[AA_bool] = AA
          
          col[aa_bool] = aa
          
          col[Aa_bool] = Aa
          
          return(col)
      
      })

      D <- (W %*% t(W)) / sum((2 * P * (1 - P))^2)
      
      A = diag(1,nrow(D))
      
      D = D * 0.99 + A * 0.01
      
      if(inv) inverse <- solve(D) else inverse <- D

  }else{
      P = apply(x,2,function(col){
        
        pi = sum(col)/(2*length(col))
        
        if(pi>0.5) pi = 1-pi
        
        return(pi)
     
      })
      Z = apply(x,2,function(col){
        pi = sum(col)/(2*length(col))

        if(pi>0.5){
        
          pi = 1-pi
        
          AA_bool = which(col == 0)
        
          aa_bool = which(col == 2)
        
          col[AA_bool] = 2
        
          col[aa_bool] = 0
        
        }
        
        col = col - 2*pi
        
        return(col)
      })
    
      G = (Z %*% t(Z)) / sum((2 * P * (1 - P)))
      
      A = diag(1,nrow(G))

      G = G * 0.99 + A * 0.01
      
      if(inv) inverse <- solve(G) else inverse <- G

  }
  return(inverse)
}

#用户可以提供的参数
ped="ped.csv"#包含ID、sire、dam三列的家系文件，必须包含表头，逗号分隔
geno="geno.csv"#包含ID和基因型数据的文件，必须包含表头，逗号分隔
id_index="id_index_sex.csv"#包含ID、selindex和sex三列的文件，必须包含表头，逗号分隔，其中selindex为选择指数，sex为性别（M或F）
t=3
male_contribution_min=2#默认雌雄1:2交配，agent可以根据用户数据或用户指定合理安排
male_contribution_max=2#默认雌雄1:2交配，agent可以根据用户数据或用户指定合理安排
female_contribution_min=1#默认雌雄1:2交配，agent可以根据用户数据或用户指定合理安排
female_contribution_max=1#默认雌雄1:2交配，agent可以根据用户数据或用户指定合理安排
n_crosses=30
diversity_mode="genomic"
use_ped = FALSE

#函数数据匹配（技能封装完成），核心原则是id和geno、rel以及ebv的排列顺序一致
fread(ped)->ped_dt
fread(geno)->geno_dt
fread(id_index)->id_index_dt
colnames(id_index_dt) = c("ID", "selindex", "sex")
male_ids = id_index_dt[sex=="M", ID]
female_ids = id_index_dt[sex=="F", ID]
candidate_ids = id_index_dt$ID
candidate_ebv = id_index_dt$selindex
female_min=rep(female_contribution_min,length(female_ids))
female_max=rep(female_contribution_max,length(female_ids))
male_min=rep(male_contribution_min,length(male_ids))
male_max=rep(male_contribution_max,length(male_ids))
lookahead_generations = t
colnames(geno_dt)[1] = "ID"
geno_dt = geno_dt[match(id_index_dt$ID, geno_dt$ID), ]

if(diversity_mode != "genomic" && use_ped){
ped_dt = visPedigree::tidyped(ped_dt,cand=id_index_dt$ID)
Amat = visPedigree::pedmat(ped_dt)
match( id_index_dt$ID,colnames(Amat)) -> idx
Amat = Amat[idx, idx]
diversity_mode = "relationship"
relationship_matrix = Amat
geno_matrix = NULL
}else if(diversity_mode != "genomic" && !use_ped){
  geno_matrix = as.matrix(geno_dt[,-1])
  relationship_matrix = makeGDE(x = geno_matrix, type="G",inv=FALSE)
  geno_matrix = NULL
}else if(diversity_mode == "genomic"){
geno_matrix = as.matrix(geno_dt[,-1])
relationship_matrix = NULL
}

#配种方案计算，来自lagm包，核心函数为lagm_plan，参数详见函数定义
mating_plan = lagm_plan(
    individual_ids = candidate_ids,
    female_ids = female_ids,
    male_ids = male_ids,
    ebv_vector = as.numeric(candidate_ebv),
    n_crosses = n_crosses,
    lookahead_generations = lookahead_generations,
    female_min = female_min,
    female_max = female_max,
    male_min = male_min,
    male_max = male_max,
    diversity_mode = diversity_mode,
    base_diversity = 1, # 不影响结果
    geno_matrix = geno_matrix,
    relationship_matrix = relationship_matrix,
    swap_prob = 0.2,
    init_prob = 0.8, # 80%的初始方案来自于启发式算法，20%来自随机生成，增加多样性
    cooling_rate = 0.998, # 👉 配合高迭代次数，放缓降温
    stop_window = 2000,   # 1000次不进步则早停
    stop_eps = 1e-8,
    n_iter = 30000,
    n_pop = 100L,
    n_threads = 8L
  )
fwrite(mating_plan, file = "mating_plan.csv", col.names = TRUE, row.names = FALSE, quote = FALSE, sep = ",", nThread = 8)