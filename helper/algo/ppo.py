import gym
import numpy as np
import argparse
import helper.envs
import torch
import torch.optim as optim
from torch.distributions import Categorical

# Computes the advantage where lambda = tau
def compute_gae(next_value, rewards, masks, values, gamma=0.99, tau=0.95):
    values = values + [next_value]
    gae = 0
    returns = []
    for step in reversed(range(len(rewards))):
        delta = rewards[step] + gamma * values[step + 1] * masks[step] - values[step]
        gae = delta + gamma * tau * masks[step] * gae
        returns.insert(0, gae + values[step])
    return returns


def ppo_iter(mini_batch_size, states, actions, log_probs, returns, advantages):
    batch_size = states.size(0)
    for _ in range(batch_size // mini_batch_size):
        rand_ids = np.random.randint(0, batch_size, mini_batch_size)
        print('OUTPUT:\n{}\n{}\n{}\n{}'.format(states, actions, log_probs, returns, advantages))
        yield states[rand_ids, :], actions[rand_ids, :], log_probs[rand_ids, :], returns[rand_ids, :], advantages[
                                                                                                       rand_ids, :]


def ppo_update(model, optimizer, ppo_epochs, mini_batch_size, states, actions, log_probs, returns, advantages,
               clip_param=0.2, evaluate=False):
    # Use Clipping Surrogate Objective to update
    for i in range(ppo_epochs):
        for state, action, log_prob, ret, advantage in ppo_iter(mini_batch_size, states, actions, log_probs, returns,
                                                                advantages):            
            dist, value = model(state)
            m = Categorical(dist)
            entropy = m.entropy().mean()
            new_log_probs = m.log_prob(action)

            ratio = (new_log_probs - log_probs).exp()
            
            surr_1 = ratio * advantage
            surr_2 = torch.clamp(ratio, 1.0 - clip_param, 1.0 + clip_param) * advantage

            # Clipped Surrogate Objective Loss
            actor_loss = torch.min(surr_1, surr_2).mean()
            # Squared Loss Function
            critic_loss = (ret - value).pow(2).mean()

            # This is L(Clip) - c_1L(VF) + c_2L(S)
            # Take negative because we're doing gradient descent
            loss = actor_loss - 0.5 * critic_loss + 0.001 * entropy

            # if (evaluate):
            #     print("ret: {} val: {}".format(ret, value))
            #     print("action: {} return: {} advantage: {} ratio: {} critic_loss: {} actor_loss: {} entropy: {} loss: {}\n".format(action.squeeze().data.item(), ret.squeeze().data.item(), advantage.squeeze().data.item(), ratio.squeeze().data.item(), critic_loss.squeeze().data.item(), actor_loss.squeeze().data.item(), entropy, loss.squeeze().data.item()))

            optimizer.zero_grad()
            loss.backward(retain_graph=model.is_recurrent)
            optimizer.step()


# Attempt to modify policy so it doesn't go too far
def ppo(model, optimizer, rl_category, num_actions, num_tasks, max_num_traj, max_traj_len, ppo_epochs, mini_batch_size, gamma, tau, clip_param, evaluate=False, is_snail=False):
    all_rewards = []
    all_states = []
    all_actions = []

    # Meta-Learning
    for task in range(num_tasks):
        task_total_rewards = []
        task_total_states = []
        task_total_actions = []
        
        print(
          "Task {} ==========================================================================================================".format(
            task))
        env = gym.make(rl_category)

        # PPO (Using actor critic style)
        for traj in range(max_num_traj):
            if (traj % 5 == 0):
                print("Trajectory {}".format(traj))
            state = env.reset()
            reward = 0.
            action = -1
            done = 0

            log_probs = []
            values = []
            states = []
            actions = []
            clean_actions = []
            rewards = []
            masks = []
            entropy = 0

            if is_snail: # variables to keep snail inputs
                snail_observations = np.array([])
                snail_actions = np.array([])
                snail_rewards = np.array([])

            for horizon in range(max_traj_len):
                state = torch.from_numpy(state).float().unsqueeze(0)

                if model.is_recurrent:
                    done_entry = torch.tensor([[done]]).float()
                    reward_entry = torch.tensor([[reward]]).float()
                    action_vector = torch.FloatTensor(num_actions)
                    action_vector.zero_()
                    if (action > -1):
                        action_vector[action] = 1
                    
                    action_vector = action_vector.unsqueeze(0)
                    
                    state = torch.cat((state, action_vector, reward_entry, done_entry), 1)
                    state = state.unsqueeze(0)

                states.append(state)

                if is_snail:
                    dist, value = model(snail_observations, snail_actions, snail_rewards)
                else:
                    dist, value = model(state)
                m = Categorical(dist)
                action = m.sample()
                print('action: {}'.format(action))

                log_prob = m.log_prob(action)
                state, reward, done, _ = env.step(action.item())

                done = int(done)
                entropy += m.entropy().mean()
                log_probs.append(log_prob.unsqueeze(0).unsqueeze(0))
                actions.append(action.unsqueeze(0).unsqueeze(0))
                clean_actions.append(action.data.item())
                
                values.append(value)
                rewards.append(reward)
                masks.append(1 - done)

                if is_snail:
                    if snail_observations.size == 0:
                        snail_observations = np.array([[state[0], done]])
                    else:
                        snail_observations = np.stack((snail_observations, np.array([[state[0], done]])),
                                                      axis=0)
                    snail_actions = np.append(snail_actions, action.item())
                    snail_rewards = np.append(snail_rewards, reward)

                if (done):
                    break

            state = torch.from_numpy(state).float().unsqueeze(0)
            if model.is_recurrent:
                done_entry = torch.tensor([[done]]).float()
                reward_entry = torch.tensor([[reward]]).float()
                action_vector = torch.FloatTensor(num_actions)
                action_vector.zero_()
                action_vector[action] = 1
                action_vector = action_vector.unsqueeze(0)
                state = torch.cat((state, action_vector, reward_entry, done_entry), 1)
                state = state.unsqueeze(0)

            if is_snail:
                _, next_val = model(snail_observations, snail_actions, snail_rewards)
            else:
                _, next_val = model(state)

            returns = compute_gae(next_val, rewards, masks, values, gamma, tau)
            returns = torch.cat(returns)
            values = torch.cat(values)
            log_probs = torch.cat(log_probs)
            states = torch.cat(states)
            actions = torch.cat(actions)
            advantage = returns - values

            task_total_rewards.append(sum(rewards))
            task_total_states.append(states)
            task_total_actions.append(clean_actions)

            # This is where we compute loss and update the model
            ppo_update(model, optimizer, ppo_epochs, mini_batch_size, states, actions, log_probs, returns, advantage, clip_param=clip_param, evaluate=evaluate)
        
        all_rewards.append(task_total_rewards)
        all_states.append(task_total_states)
        all_actions.append(task_total_actions)
        if model.is_recurrent:
            model.reset_hidden_state()
    return all_rewards, all_states, all_actions, model
