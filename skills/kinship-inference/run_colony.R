threads <- 45   ## Number of threads to use for COLONY
cmd <- sprintf("nohup /opt/intel/oneapi/mpi/2021.10.0/bin/mpirun -np %d /home/qianggf/softwares/colony/colony2p.ifort.impi2018.out IFN:colony.dat &", threads)

status <- system(cmd)

if (status != 0) {
  stop(sprintf("Failed to start COLONY command, exit status: %s", status))
}

message("COLONY command started successfully.")
