"""Minimal MLX data sharding (no training / no gradients).

Orchestration matches notebooks/runtime/04_mlx_data_parallelism.ipynb:
  1) make_data -> full (X, y)
  2) X[rank::size] -> local shard
  3) print local n and mean(X)

Run with 3 processes:
  mlx.launch -n 3 -- python notebooks/runtime/dp_train_min.py
"""

from __future__ import annotations

import numpy as np

import mlx.core as mx


SEED = 0
N = 300


def make_data(n: int = N, seed: int = SEED):
    """Full dataset only; sharding is orchestration in main (X[rank::size])."""
    mx.random.seed(seed)
    np.random.seed(seed)
    n0, n1 = n // 2, n - n // 2
    X0 = mx.random.normal((n0, 2)) + mx.array([-1.2, -0.8])
    X1 = mx.random.normal((n1, 2)) + mx.array([1.2, 0.8])
    X = mx.concatenate([X0, X1], axis=0)
    y = mx.concatenate(
        [mx.zeros((n0,), dtype=mx.uint32), mx.ones((n1,), dtype=mx.uint32)]
    )
    perm = mx.array(np.random.permutation(n))
    X, y = X[perm], y[perm]
    mx.eval(X, y)
    return X, y


def main():
    world = mx.distributed.init()
    rank, size = world.rank(), world.size()

    X, y = make_data()
    X_local, y_local = X[rank::size], y[rank::size]
    mean_local = mx.mean(X_local, axis=0)
    mx.eval(X_local, y_local, mean_local)

    print(
        f"[rank {rank}/{size}] local n={X_local.shape[0]} "
        f"(global N={X.shape[0]}) "
        f"pos={(y_local == 1).sum().item()} "
        f"neg={(y_local == 0).sum().item()} "
        f"mean(X)={np.array(mean_local)}"
    )


if __name__ == "__main__":
    main()
