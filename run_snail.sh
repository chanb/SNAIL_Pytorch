num_traj=10
batchsize=10000
minibatchsize=256
num_tasks=25000
epochs=5
lr=3e-4
clip_param=0.1
num_workers=3

python rl2_train.py --model_type snail --out_file test_snail.pt --batch_size $batchsize --num_tasks $num_tasks --mini_batch_size $minibatchsize --num_traj $num_traj --tau 0.3 --gamma 0.99 --ppo_epochs $epochs --learning_rate $lr --clip_param $clip_param --num_workers=3
python rl2_eval.py --algo ppo --eval_tasks ./experiments/bandit_5_1000.pkl --out_file result_snail.pkl --eval_model test_snail.pt --num_traj $num_traj
python read_result.py --file result_snail.pkl --task bandit --out_file exp1_snail

# python rl2_train.py --out_file test.pt --batch_size 15 --num_tasks 1 --mini_batch_size 5 --num_traj 100 --tau 0.3 --gamma 0.99 --learning_rate 0.05 --ppo_epochs 3 --clip_param 0.2

# MDP Task
# python rl2_train.py --out_file test.pt --batch_size 15 --num_tasks 6 --mini_batch_size 10 --num_traj 6 --tau 0.3 --gamma 0.99 --learning_rate 0.05 --ppo_epochs 3 --clip_param 0.2 --traj_len 10 --task mdp