Development
===========

During development, one needs to pass a relative path:

.. code:: json

   "matrix": {
       "req": {
           "asv_bench_memray": ["../asv_bench_memray"]
       },
   },

Also it may be necessary to cleanup older environments and explicitly
point to an instance of ``asv_runner``:

.. code:: sh

   rm -rf .asv && ASV_RUNNER_PATH="../asv_runner" asv run --bench sum

Personally I keep benchmarks for testing at an `experiments
repo <https://github.com/HaoZeke/asv_experiments>`__, but any local test
will do.

Conventions
-----------

Like all externally defined benchmark plugins for ``asv``, this has a strict hierarchy:

- The package name begins with ``asv_bench``.
- Benchmarks are defined in a ``benchmarks`` folder under the package module.
- Each exported new benchmark type has the ``export_as_benchmark = [NAMEBenchmark]`` attribute.

For more conventions, follow the documentation of ``asv_runner``.
