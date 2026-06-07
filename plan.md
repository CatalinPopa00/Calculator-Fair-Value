1. Modify `scraper/yahoo.py:search_companies` to use `concurrent.futures.ThreadPoolExecutor` for parallel requests.
2. Ensure we still filter the result and return exactly as before. The first successful request should break the loop and return.
3. Shutdown the executor gracefully with `wait=False, cancel_futures=True` to immediately return the result without blocking on any timed-out or pending requests.
4. Verify by running format, lint checks, and the full test suite. Make sure the results are identical to the sequential approach.
5. Create a pull request documenting the change and the benchmarked improvement.
