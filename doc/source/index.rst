ASV Memray Benchmark Plugin documentation
=========================================

``asv_bench_memray`` is an externally defined ``memray`` benchmark plugin for
:doc:`asv <asv:index>` using :doc:`asv_runner <asv_runner:index>`.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   development
   apidocs/index

Usage
=====

In your ``asv.conf.json`` add the following to the requirements matrix:

.. code:: json

   "matrix": {
       "req": {
           "numpy": ["1.21"],
           "asv_plugin_memray": [""]
       },
   },

This should be enough for an example like the following to run:

.. code:: python

   import numpy as np

   class MyBenchmark:
       params = [10, int(2e4)]

       def ray_sum(self, n):
           self.data = np.random.rand(n)
           np.sum(self.data)

Which should result in something roughly like:

.. code:: sh

   ASV_RUNNER_PATH="../asv_runner" asv run --bench sum
   · Creating environments.......
   · Discovering benchmarks
   ·· Uninstalling from virtualenv-py3.9-asv_bench_memray.._asv_bench_memray-numpy1.21
   ·· Building 30a650cb <main> for virtualenv-py3.9-asv_bench_memray.._asv_bench_memray-numpy1.21.
   ·· Installing 30a650cb <main> into virtualenv-py3.9-asv_bench_memray.._asv_bench_memray-numpy1.21
   · Running 1 total benchmarks (1 commits * 1 environments * 1 benchmarks)
   [ 0.00%] · For project commit 30a650cb <main>:
   [ 0.00%] ·· Benchmarking virtualenv-py3.9-asv_bench_memray.._asv_bench_memray-numpy1.21
   [100.00%] ··· benchmarks.MyBenchmark.ray_sum                                                ok
   [100.00%] ··· ======== =======
                  param1
                 -------- -------
                    10     1.72k
                  20000     162k
                 ======== =======

   ASV_RUNNER_PATH="../asv_runner" asv run --bench sum  8.72s user 3.04s system 99% cpu 11.877 total


.. note::

    The GitHub repository at `asv_samples
    <https://github.com/HaoZeke/asv_samples>`_ has a dedicated branch for
    testing ``asv_bench_memray``.

License
-------

MIT.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
