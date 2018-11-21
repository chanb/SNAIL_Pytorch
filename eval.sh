#!/usr/bin/env bash

arms=( 5 10 50 )
tasks=( bandit mdp )
num_tasks=100

algos=( rl2 snail maml )
trajs=( 10 100 500 1000 )

for task in ${tasks[@]}; do
    if [ $task == "bandit" ]; then
    actions=$arms
     else
        actions=( 5 )
     fi
    for action in ${actions[@]}; do
        python generate_experiments.py --num_tasks $num_tasks --num_actions $action --task $task
    done
done

for task in ${tasks[@]}; do
    if [ $task == "bandit" ]; then
        actions=$arms
    else
       actions=( 5 )
    fi
    for traj in ${trajs[@]}; do
        for action in ${actions[@]}; do
            for algo in ${algos[@]}; do
                python evaluate_model.py --num_tasks $num_tasks --num_actions $action --task $task \
                    --eval_model ./saves/$algo/$task_"$action"_"$traj".pt
                    --eval_tasks ./experiments/"$task"_"$action"_"$num_tasks".pkl
                mkdir $algo/logs_eval/$algo
                mv ./logs_eval/"$task"_"$action"_"$num_tasks".pkl ./logs_eval/$algo/"$task"_"$action"_"$traj".pkl
            done
        done
    done
done