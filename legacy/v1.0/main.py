import asyncio
import platform
from game import MemtrixGame

async def main():
    game = MemtrixGame()
    await game.run()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())