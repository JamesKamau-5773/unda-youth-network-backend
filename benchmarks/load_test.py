"""Simple asyncio-based load tester using aiohttp.

Usage: python3 benchmarks/load_test.py http://localhost:5000/ 100 10
  args: target_url, total_requests, concurrency
"""
import asyncio
import sys
import time
from aiohttp import ClientSession


async def worker(name, queue, session, results):
    while True:
        url = await queue.get()
        if url is None:
            queue.task_done()
            break
        start = time.time()
        try:
            async with session.get(url, timeout=10) as resp:
                await resp.text()
                results.append((resp.status, time.time() - start))
        except Exception as e:
            results.append((0, time.time() - start))
        queue.task_done()


async def run(target, total, concurrency):
    queue = asyncio.Queue()
    for _ in range(total):
        await queue.put(target)
    for _ in range(concurrency):
        await queue.put(None)

    results = []
    async with ClientSession() as session:
        tasks = [asyncio.create_task(worker(f'w{i}', queue, session, results)) for i in range(concurrency)]
        await queue.join()
        for t in tasks:
            t.cancel()

    # Summarize
    statuses = {}
    latencies = [r[1] for r in results]
    for s, _ in results:
        statuses[s] = statuses.get(s, 0) + 1
    print('Results:')
    print('  Total requests:', len(results))
    print('  Status counts:', statuses)
    if latencies:
        print('  Avg latency: {:.3f}s'.format(sum(latencies)/len(latencies)))
        print('  P95 latency: {:.3f}s'.format(sorted(latencies)[int(0.95*len(latencies))-1]))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python3 load_test.py <url> <total_requests> <concurrency>')
        sys.exit(1)
    target = sys.argv[1]
    total = int(sys.argv[2])
    concurrency = int(sys.argv[3])
    asyncio.run(run(target, total, concurrency))
