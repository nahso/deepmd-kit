# SPDX-License-Identifier: LGPL-3.0-or-later
import copy
import unittest

import numpy as np
import torch

from deepmd.pt.model.model import (
    get_model,
)
from deepmd.pt.utils import (
    env,
)

dtype = torch.float64

from .test_permutation import (
    eval_model,
    make_sample,
    model_dpa1,
    model_dpa2,
    model_se_e2_a,
)


# from deepmd-kit repo
def finite_difference(f, x, delta=1e-6):
    in_shape = x.shape
    y0 = f(x)
    out_shape = y0.shape
    res = np.empty(out_shape + in_shape)
    for idx in np.ndindex(*in_shape):
        diff = np.zeros(in_shape)
        diff[idx] += delta
        y1p = f(x + diff)
        y1n = f(x - diff)
        res[(Ellipsis, *idx)] = (y1p - y1n) / (2 * delta)
    return res


def stretch_box(old_coord, old_box, new_box):
    ocoord = old_coord.reshape(-1, 3)
    obox = old_box.reshape(3, 3)
    nbox = new_box.reshape(3, 3)
    ncoord = ocoord @ np.linalg.inv(obox) @ nbox
    return ncoord.reshape(old_coord.shape)


class ForceTest:
    def test(
        self,
    ):
        places = 8
        delta = 1e-5
        natoms = 5
        cell = torch.rand([3, 3], dtype=dtype)
        cell = (cell + cell.T) + 5.0 * torch.eye(3)
        coord = torch.rand([natoms, 3], dtype=dtype)
        coord = torch.matmul(coord, cell)
        atype = torch.IntTensor([0, 0, 0, 1, 1])
        # assumes input to be numpy tensor
        coord = coord.numpy()

        def np_infer(
            coord,
        ):
            e0, f0, v0 = eval_model(
                self.model, torch.tensor(coord).unsqueeze(0), cell.unsqueeze(0), atype
            )
            ret = {
                "energy": e0.squeeze(0),
                "force": f0.squeeze(0),
                "virial": v0.squeeze(0),
            }
            # detach
            ret = {kk: ret[kk].detach().cpu().numpy() for kk in ret}
            return ret

        def ff(_coord):
            return np_infer(_coord)["energy"]

        fdf = -finite_difference(ff, coord, delta=delta).squeeze()
        rff = np_infer(coord)["force"]
        np.testing.assert_almost_equal(fdf, rff, decimal=places)


class VirialTest:
    def test(
        self,
    ):
        places = 8
        delta = 1e-4
        natoms = 5
        cell = torch.rand([3, 3], dtype=dtype)
        cell = (cell) + 5.0 * torch.eye(3)
        coord = torch.rand([natoms, 3], dtype=dtype)
        coord = torch.matmul(coord, cell)
        atype = torch.IntTensor([0, 0, 0, 1, 1])
        # assumes input to be numpy tensor
        coord = coord.numpy()
        cell = cell.numpy()

        def np_infer(
            new_cell,
        ):
            e0, f0, v0 = eval_model(
                self.model,
                torch.tensor(stretch_box(coord, cell, new_cell)).unsqueeze(0),
                torch.tensor(new_cell).unsqueeze(0),
                atype,
            )
            ret = {
                "energy": e0.squeeze(0),
                "force": f0.squeeze(0),
                "virial": v0.squeeze(0),
            }
            # detach
            ret = {kk: ret[kk].detach().cpu().numpy() for kk in ret}
            return ret

        def ff(bb):
            return np_infer(bb)["energy"]

        fdv = -(
            finite_difference(ff, cell, delta=delta).transpose(0, 2, 1) @ cell
        ).squeeze()
        rfv = np_infer(cell)["virial"]
        np.testing.assert_almost_equal(fdv, rfv, decimal=places)


class TestEnergyModelSeAForce(unittest.TestCase, ForceTest):
    def setUp(self):
        model_params = copy.deepcopy(model_se_e2_a)
        sampled = make_sample(model_params)
        self.type_split = False
        self.model = get_model(model_params, sampled).to(env.DEVICE)


class TestEnergyModelSeAVirial(unittest.TestCase, VirialTest):
    def setUp(self):
        model_params = copy.deepcopy(model_se_e2_a)
        sampled = make_sample(model_params)
        self.type_split = False
        self.model = get_model(model_params, sampled).to(env.DEVICE)


class TestEnergyModelDPA1Force(unittest.TestCase, ForceTest):
    def setUp(self):
        model_params = copy.deepcopy(model_dpa1)
        sampled = make_sample(model_params)
        self.type_split = True
        self.model = get_model(model_params, sampled).to(env.DEVICE)


class TestEnergyModelDPA1Virial(unittest.TestCase, VirialTest):
    def setUp(self):
        model_params = copy.deepcopy(model_dpa1)
        sampled = make_sample(model_params)
        self.type_split = True
        self.model = get_model(model_params, sampled).to(env.DEVICE)


class TestEnergyModelDPA2Force(unittest.TestCase, ForceTest):
    def setUp(self):
        model_params_sample = copy.deepcopy(model_dpa2)
        model_params_sample["descriptor"]["rcut"] = model_params_sample["descriptor"][
            "repinit_rcut"
        ]
        model_params_sample["descriptor"]["sel"] = model_params_sample["descriptor"][
            "repinit_nsel"
        ]
        sampled = make_sample(model_params_sample)
        model_params = copy.deepcopy(model_dpa2)
        self.type_split = True
        self.model = get_model(model_params, sampled).to(env.DEVICE)


class TestEnergyModelDPAUniVirial(unittest.TestCase, VirialTest):
    def setUp(self):
        model_params_sample = copy.deepcopy(model_dpa2)
        model_params_sample["descriptor"]["rcut"] = model_params_sample["descriptor"][
            "repinit_rcut"
        ]
        model_params_sample["descriptor"]["sel"] = model_params_sample["descriptor"][
            "repinit_nsel"
        ]
        sampled = make_sample(model_params_sample)
        model_params = copy.deepcopy(model_dpa2)
        self.type_split = True
        self.model = get_model(model_params, sampled).to(env.DEVICE)