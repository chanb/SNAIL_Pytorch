import multiprocessing as mp
from multiprocessing.pool import ThreadPool
import gym
import numpy as np

import torch

from helper.sampler import Sampler

# Samples from multiple tasks using a given model
def evaluate_multiple_tasks(device, env_name, eval_model, tasks, num_actions, num_traj, traj_len, num_workers=3):
  print('Testing model: {}'.format(eval_model))
  pool = ThreadPool(processes=num_workers)

  results = [pool.apply(evaluate_single_task, args=(device, eval_model, env_name, num_actions, task, num_traj, traj_len)) for task in tasks]

  all_rewards, all_actions, all_states = zip(*results)
  return all_rewards, all_actions, all_states


# Samples from a single task using a given model
def evaluate_single_task(device, eval_model, env_name, num_actions, task, num_traj, traj_len):
  task_rewards = []
  task_states = []
  task_actions = []
  model = torch.load(eval_model).to(device)
  sampler = Sampler(device, model, env_name, num_actions, num_workers=1, evaluate=True)
  sampler.set_task(task)
  sampler.sample(num_traj * traj_len)

  # Sample a total of num_traj * traj_len
  # Format it so we store 1 trajectory at a time
  for i in range(num_traj):
    curr_traj_actions = []
    curr_traj_states = []
    curr_traj_rewards = 0

    for j in range(traj_len):
      curr_idx = i * j + i
      # Make sure the list is readable for humans...
      curr_traj_actions.append(sampler.clean_actions[curr_idx].squeeze(0).data.item())
      curr_traj_states.append(sampler.clean_states[curr_idx].squeeze(0).squeeze(0).tolist())
      curr_traj_rewards += sampler.clean_rewards[curr_idx].data.item()
      
    task_rewards.append(curr_traj_rewards)
    task_states.append(curr_traj_states)
    task_actions.append(curr_traj_actions)

  sampler.envs.close()
  return sum(task_rewards), task_actions, task_states


# Samples from multiple tasks randomly
def sample_multiple_random_fixed_length(env_name, tasks, num_actions, num_traj, traj_len, num_workers=3):
  pool = mp.Pool(processes=num_workers)

  results = [pool.apply(random_single_task, args=(gym.make(env_name), task, num_actions, num_traj, traj_len)) for task in tasks]

  all_rewards, all_actions, all_states = zip(*results)

  return all_rewards, all_actions, all_states

# Samples from a single task randomly
def random_single_task(env, task, num_actions, num_traj, traj_len):
  env.unwrapped.reset_task(task)
  task_rewards = []
  task_states = []
  task_actions = []
  
  # Sample a total of num_traj * traj_len
  # Format it so we store 1 trajectory at a time
  for _ in range(num_traj):
    curr_traj_actions = []
    curr_traj_states = []
    curr_traj_rewards = 0

    env.reset()
    for _ in range(traj_len):
      action = np.random.randint(0, num_actions)
      state, reward, _, _ = env.step(action)
      
      curr_traj_rewards += reward
      curr_traj_actions.append(action)
      curr_traj_states.append(state)

    task_rewards.append(curr_traj_rewards)
    task_states.append(curr_traj_actions)
    task_actions.append(curr_traj_states)

  return task_rewards, task_actions, task_states