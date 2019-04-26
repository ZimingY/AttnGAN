[1]. def encode_image_by_16times_WGAN(ndf):
first layer 去掉norm

[2]. in trainer: cond_wrong_errD.backward(one or mone)

[3]. utils.py lambda_term = 1

[4]. DAMSM loss should be changed? it has log

[5]. changed adam parameters

[6]. trainer_WGAN,  for p, avg_p in zip(netG.parameters(), avg_param_G):
                avg_p.mul_(0.999).add_(0.001, p.data)


[]. ssh -L localhost:8888:localhost:6006 ziming@scheduler.cs.toronto.edu

[]. ssh ziming@scheduler.cs.toronto.edu
	sinfo -aNo "%N %T %.4c %.8z %.6m %20f" 
	srun --partition=gpunodes  --nodelist=gpunode12 --mail-type=ALL,TIME_LIMIT_90 --mail-user=ziming@cs.toronto.edu  --pty bash --login
	srun --partition=gpunodes  --nodelist=gpunode12 --pty bash --login
	
	squeue -o "%N %.8u %.20e"

batch size = 8

errD0: 0.63 errD1: 0.93 errD2: 0.60 
g_loss0: 7.06 g_loss1: 5.83 g_loss2: 13.36 w_loss: 23.69 s_loss: 21.85 kl_loss: 0.01 
errD0: 0.56 errD1: 0.59 errD2: 1.08 
g_loss0: 7.26 g_loss1: 11.41 g_loss2: 3.14 w_loss: 20.42 s_loss: 21.61 kl_loss: 0.01 
errD0: 0.83 errD1: 0.64 errD2: 0.76 
g_loss0: 10.04 g_loss1: 13.96 g_loss2: 9.29 w_loss: 19.33 s_loss: 17.80 kl_loss: 0.01 
errD0: 0.72 errD1: 1.32 errD2: 0.69 
g_loss0: 5.00 g_loss1: 4.80 g_loss2: 6.53 w_loss: 20.98 s_loss: 16.82 kl_loss: 0.01 
errD0: 0.33 errD1: 0.49 errD2: 1.36 
g_loss0: 11.10 g_loss1: 15.40 g_loss2: 2.19 w_loss: 10.55 s_loss: 11.63 kl_loss: 0.01 
errD0: 0.68 errD1: 0.84 errD2: 0.67 
g_loss0: 7.93 g_loss1: 9.97 g_loss2: 13.89 w_loss: 18.56 s_loss: 13.26 kl_loss: 0.01 
errD0: 0.18 errD1: 0.70 errD2: 0.87 
g_loss0: 12.87 g_loss1: 16.19 g_loss2: 3.03 w_loss: 17.83 s_loss: 14.13 kl_loss: 0.01 
errD0: 0.49 errD1: 0.41 errD2: 0.60 
g_loss0: 16.25 g_loss1: 18.78 g_loss2: 10.25 w_loss: 15.34 s_loss: 14.63 kl_loss: 0.01 
errD0: 0.23 errD1: 0.60 errD2: 0.38 
g_loss0: 13.96 g_loss1: 9.28 g_loss2: 12.36 w_loss: 12.62 s_loss: 13.04 kl_loss: 0.02 
errD0: 0.12 errD1: 0.80 errD2: 0.82 
g_loss0: 12.27 g_loss1: 5.78 g_loss2: 4.34 w_loss: 8.84 s_loss: 10.53 kl_loss: 0.02 

errD0: 0.06 errD1: 0.31 errD2: 0.16 
g_loss0: 13.75 g_loss1: 10.16 g_loss2: 9.40 w_loss: 6.84 s_loss: 7.46 kl_loss: 0.02 
[0/1200][1106]
                  Loss_D: 1.38 Loss_G: 61.66 Time: 536.15s
Save G/Ds models.
errD0: 4.71 errD1: 4.00 errD2: 0.35 
g_loss0: 2.28 g_loss1: 4.80 g_loss2: 10.63 w_loss: 13.10 s_loss: 10.82 kl_loss: 0.01 
errD0: 0.26 errD1: 0.55 errD2: 0.33 
g_loss0: 8.52 g_loss1: 7.46 g_loss2: 9.54 w_loss: 7.01 s_loss: 9.85 kl_loss: 0.02 
errD0: 0.34 errD1: 0.60 errD2: 0.94 
g_loss0: 9.90 g_loss1: 8.04 g_loss2: 7.29 w_loss: 9.84 s_loss: 10.13 kl_loss: 0.02 
errD0: 0.85 errD1: 0.60 errD2: 0.96 
g_loss0: 2.52 g_loss1: 13.51 g_loss2: 2.73 w_loss: 7.25 s_loss: 7.50 kl_loss: 0.02 
errD0: 3.00 errD1: 0.68 errD2: 4.06 
g_loss0: 3.67 g_loss1: 12.42 g_loss2: 0.21 w_loss: 6.54 s_loss: 8.92 kl_loss: 0.02 


batch size = 14
errD0: 0.57 errD1: 0.49 errD2: 0.76 
g_loss0: 7.76 g_loss1: 9.46 g_loss2: 11.12 w_loss: 27.61 s_loss: 26.04 kl_loss: 0.01 
errD0: 0.59 errD1: 0.61 errD2: 0.44 
g_loss0: 8.70 g_loss1: 7.44 g_loss2: 13.33 w_loss: 28.14 s_loss: 24.44 kl_loss: 0.01 
errD0: 0.61 errD1: 0.37 errD2: 0.81 
g_loss0: 9.31 g_loss1: 10.71 g_loss2: 2.83 w_loss: 21.72 s_loss: 18.75 kl_loss: 0.01 
errD0: 0.18 errD1: 0.20 errD2: 0.38 
g_loss0: 12.41 g_loss1: 10.83 g_loss2: 12.98 w_loss: 20.62 s_loss: 18.65 kl_loss: 0.01 
errD0: 0.85 errD1: 1.52 errD2: 0.63 
g_loss0: 9.64 g_loss1: 13.77 g_loss2: 12.94 w_loss: 18.67 s_loss: 20.14 kl_loss: 0.01 
errD0: 0.24 errD1: 0.44 errD2: 0.87 
g_loss0: 8.55 g_loss1: 16.95 g_loss2: 7.16 w_loss: 13.92 s_loss: 15.69 kl_loss: 0.01 
[0/600][632]
                  Loss_D: 1.57 Loss_G: 76.81 Time: 429.43s
Save G/Ds models.
errD0: 0.03 errD1: 0.25 errD2: 0.25 
g_loss0: 10.30 g_loss1: 8.16 g_loss2: 4.76 w_loss: 8.27 s_loss: 11.13 kl_loss: 0.01 
errD0: 0.26 errD1: 0.83 errD2: 0.40 
g_loss0: 12.53 g_loss1: 13.04 g_loss2: 10.06 w_loss: 12.01 s_loss: 15.90 kl_loss: 0.01 
errD0: 0.52 errD1: 0.45 errD2: 0.57 
g_loss0: 12.50 g_loss1: 11.77 g_loss2: 14.54 w_loss: 18.93 s_loss: 14.23 kl_loss: 0.02