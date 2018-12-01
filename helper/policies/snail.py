import torch
import torch.nn as nn
import numpy as np
from torch.distributions import Categorical
from helper.policies.policy import Policy
from helper.snail_blocks import *

class LinearEmbedding(Policy):
  def __init__(self, input_size=1, output_size=32):
    super(LinearEmbedding, self).__init__(input_size, output_size)
    self.fcn = nn.Linear(input_size, output_size)

  def forward(self, x):
    return self.fcn(x)


class SNAILPolicy(Policy):
  # K arms, trajectory of length N
  def __init__(self, output_size, max_num_traj, max_traj_len, encoder, input_size=1, hidden_size=32, num_traj=1):
    super(SNAILPolicy, self).__init__(input_size, output_size)
    self.K = output_size
    self.N = max_num_traj
    self.T = max_num_traj * max_traj_len
    self.hidden_size = hidden_size
    self.is_recurrent = True
    
    num_channels = 0

    self.encoder = encoder
    num_channels += hidden_size

    num_filters = int(math.ceil(math.log(self.T)))

    self.tc_1 = TCBlock(num_channels, self.T, hidden_size)
    num_channels += num_filters * hidden_size

    self.tc_2 = TCBlock(num_channels, self.T, hidden_size)
    num_channels += num_filters * hidden_size

    self.attention_1 = AttentionBlock(num_channels, hidden_size, hidden_size)
    num_channels += hidden_size

    self.affine_2 = nn.Linear(num_channels, self.K)


  def forward(self, x, hidden_state):
    if hidden_state.size()[0] == 0:
      x = x
    elif hidden_state.shape[0] >= self.T:
      x = torch.cat((hidden_state[1:(self.T), :, :], x))
    else:
      x = torch.cat((hidden_state, x))

    next_hidden_state = x

    if x.shape[0] < self.T:
      x = torch.cat((torch.FloatTensor(self.T - x.shape[0], x.shape[1], x.shape[2]).zero_(), x))

    x = self.encoder(x) # result: traj_len x 32
    x = self.tc_1(x)
    x = self.tc_2(x)
    x = self.attention_1(x)
    x = self.affine_2(x)
    x = x[self.T-1, :, :] # pick_last_action
    return Categorical(logit = x), next_hidden_state
