# PFLlib: Personalized Federated Learning Algorithm Library
# Copyright (C) 2021  Jianqing Zhang

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import torch
from torch.optim import Optimizer


class PerAvgOptimizer(Optimizer):
    def __init__(self, params, lr):
        defaults = dict(lr=lr)
        super(PerAvgOptimizer, self).__init__(params, defaults)

    def step(self, beta=0):
        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue
                d_p = p.grad.data
                if(beta != 0):
                    p.data.add_(other=d_p, alpha=-beta)
                else:
                    p.data.add_(other=d_p, alpha=-group['lr'])


class SCAFFOLDOptimizer(Optimizer):
    def __init__(self, params, lr):
        defaults = dict(lr=lr)
        super(SCAFFOLDOptimizer, self).__init__(params, defaults)

    def step(self, server_cs, client_cs):
        for group in self.param_groups:
            for p, sc, cc in zip(group['params'], server_cs, client_cs):
                p.data.add_(other=(p.grad.data + sc - cc), alpha=-group['lr'])


# class pFedMeOptimizer(Optimizer):
#     def __init__(self, params, lr=0.01, lamda=0.1, mu=0.001):
#         defaults = dict(lr=lr, lamda=lamda, mu=mu)
#         super(pFedMeOptimizer, self).__init__(params, defaults)
#
#     def step(self, local_model, device):
#         group = None
#         weight_update = local_model.copy()
#         for group in self.param_groups:
#             for p, localweight in zip(group['params'], weight_update):
#                 localweight = localweight.to(device)
#                 # approximate local model
#                 p.data = p.data - group['lr'] * (p.grad.data + group['lamda'] * (p.data - localweight.data) + group['mu'] * p.data)
#
#         return group['params']


class pFedMeOptimizer(torch.optim.Adam):
    def __init__(self, params, lr=0.01, lamda=0.1, mu=0.001, betas=(0.9, 0.999), eps=1e-8):
        # Initialize the parent class (Adam)
        super(pFedMeOptimizer, self).__init__(params, lr=lr, betas=betas, eps=eps)
        self.lamda = lamda
        self.mu = mu


    @torch.no_grad()
    def step(self, local_model=None, device=None):
        """
        Performs a single optimization step, which includes the pFedMe personalization adjustments.

        Args:
        - local_model: Local model parameters for personalization.
        - device: The device on which the optimizer operates.
        """
        # This calls the Adam step for all parameters at once
        super(pFedMeOptimizer, self).step()

        # Validate if local_model and device are provided
        if local_model is None or device is None:
            raise ValueError("local_model and device must be provided for pFedMeOptimizer.")

        for group in self.param_groups:
            for p, local_weight in zip(group['params'], local_model):
                if p.grad is None:
                    continue
                grad = p.grad.data

                # Ensure local_weight is on the correct device
                local_weight = local_weight.to(device)

                # Personalization adjustment based on the local model
                p.data.sub_(self.lamda * (p.data - local_weight) + self.mu * p.data, alpha=group['lr'])

        return group['params']


class APFLOptimizer(Optimizer):
    def __init__(self, params, lr):
        defaults = dict(lr=lr)
        super(APFLOptimizer, self).__init__(params, defaults)

    def step(self, beta=1, n_k=1):
        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue
                d_p = beta * n_k * p.grad.data
                p.data.add_(-group['lr'], d_p)


class PerturbedGradientDescent(Optimizer):
    def __init__(self, params, lr=0.01, mu=0.0):
        default = dict(lr=lr, mu=mu)
        super().__init__(params, default)

    @torch.no_grad()
    def step(self, global_params, device):
        for group in self.param_groups:
            for p, g in zip(group['params'], global_params):
                g = g.to(device)
                d_p = p.grad.data + group['mu'] * (p.data - g.data)
                p.data.add_(d_p, alpha=-group['lr'])