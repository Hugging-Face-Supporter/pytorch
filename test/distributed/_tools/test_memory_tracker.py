# Owner(s): ["oncall: distributed"]

from torch.testing._internal.common_cuda import TEST_CUDA
from torch.testing._internal.common_utils import (
    TestCase,
    run_tests,
)

import torch
import torch.nn as nn

from torch.distributed._tools import MemoryTracker

import unittest


class TestMemoryTracker(TestCase):
    @unittest.skipIf(not TEST_CUDA, "no cuda")
    def test_local_model(self):
        """
        Minimal test case to check the memory tracker can collect the expected
        memory stats at operator level, as well as can print the summary result
        without crash.
        """
        # Create a model with a hierarchy of modules
        torch.manual_seed(0)
        model = nn.Sequential(
            nn.Sequential(
                nn.Conv2d(3, 64, kernel_size=(3, 3), padding=(1, 1), bias=False),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=False),
                nn.AdaptiveAvgPool2d(output_size=(1, 1)),
            ),
            nn.Flatten(start_dim=1),
            nn.Sequential(nn.Linear(64, 2), nn.ReLU(inplace=True)),
        ).cuda()

        # Run one iteration of forward and backward pass
        tracker = MemoryTracker()
        tracker.start_monitor(model)

        x = torch.randn(size=(2, 3, 224, 224), device=torch.device("cuda"))
        # torch.LongTensor expects cpu device type, not cuda device type in
        # constructor, so calling .cuda() outside constructor here.
        target = torch.LongTensor([0, 1]).cuda()
        criterion = nn.CrossEntropyLoss()
        criterion(model(x), target).backward()

        self.assertTrue(len(tracker._hooks) > 0)

        tracker.stop()

        self.assertTrue(len(tracker._hooks) == 0)

        tracker.summary()

        self.assertTrue(tracker._op_index > 0)
        self.assertTrue(len(tracker._operator_names) > 0)
        self.assertEqual(len(tracker.memories_allocated), tracker._op_index)
        self.assertEqual(len(tracker.memories_active), tracker._op_index)
        self.assertEqual(len(tracker.memories_reserved), tracker._op_index)
        self.assertTrue(len(tracker._markers) == 2)
        self.assertTrue(tracker._cur_module_name != "")


if __name__ == "__main__":
    run_tests()
