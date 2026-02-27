for filename in os.listdir("./cogs"):

    if filename.endswith(".py") and filename != "__init__.py":

        await bot.load_extension(f"cogs.{filename[:-3]}")


