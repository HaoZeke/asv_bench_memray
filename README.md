# asv_bench_memray

This a proof-of-concept externally defined `memray` **benchmark plugin** for `asv`.

## Usage

In your `asv.conf.json` add the following to the requirements matrix:

``` json-with-comments
"matrix": {
    "req": {
        "numpy": ["1.21"],
        "asv_bench_memray": [""]
    },
},
```

This should be enough for an example like the following to run:

``` python
import numpy as np

class MyBenchmark:
    params = [10, int(2e4)]

    def ray_sum(self, n):
        self.data = np.random.rand(n)
        np.sum(self.data)
```

Which should result in something roughly like:

```sh
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
```

## Allocator tracing, warmup, and repeat

`warmup_time` and `repeat` use the same attribute names as timing benchmarks. Warmup calls run outside the tracker. Each repeat is its own memray capture. A `repeat` of 1 (the default) returns that peak as an integer. A larger count, or a `(min_repeat, max_repeat, max_time)` triple, returns `{"samples": [...], "number": 1}` so asv reports the median. The default warmup is 0 seconds.

`ray_trace_python_allocators` records allocations served by Python's pymalloc allocator. `ray_native_traces` records native stack frames. Both default to off. The same switches exist as `ASV_BENCH_MEMRAY_TRACE_PYTHON_ALLOCATORS` and `ASV_BENCH_MEMRAY_NATIVE_TRACES`.

```python
class MyBenchmark:
    warmup_time = 0.1
    repeat = 3

    def ray_sum(self, n):
        self.data = bytearray(n)

    ray_sum.ray_trace_python_allocators = True
    ray_sum.ray_native_traces = False
```

`asv run --quick` still forces `repeat = 1` and `warmup_time = 0`. When a profile is saved, the HTML is the last sample.

## Development

During development, one needs to pass a relative path:

``` json-with-comments
"matrix": {
    "req": {
        "asv_bench_memray": ["../asv_bench_memray"]
    },
},
```

Also it may be necessary to cleanup older environments and explicitly point to an instance of `asv_runner`:

``` sh
rm -rf .asv && ASV_RUNNER_PATH="../asv_runner" asv run --bench sum
```

Personally I keep benchmarks for testing at an [experiments repo](https://github.com/HaoZeke/asv_experiments), but any local test will do.

### Conventions

Like all externally defined benchmark plugins for `asv`, this has a strict hierarchy.
- [X] The package name begins with `asv_bench`
- [X] Benchmarks are defined in a `benchmarks` folder under the package module
- [X] Each exported new benchmark type has the `export_as_benchmark = [NAMEBenchmark]` attribute

For more conventions follow the documention of `asv_runner`.

# License
MIT.


## asv-tachyon profile integration

Pair with [asv-tachyon](https://github.com/HaoZeke/asv_tachyon) so Explore can
open memray HTML for `ray_*` benchmarks:

```bash
ASV_BENCH_MEMRAY_PROFILE=1 asv run --bench ray_
# or per-benchmark: ray_sum.ray_save_profile = True

asv publish
python -m asv_bench_memray profiles publish --html-dir .asv/html
asv-tachyon serve .asv/html --open
```

Artifacts: `.asv/profiles/memray/` (or `ASV_BENCH_MEMRAY_PROFILE_DIR`).
Publish merges into the same `profiles.json` as asv_bench_tachyon.

