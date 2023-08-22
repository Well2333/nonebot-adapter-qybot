import nonebot

from nonebot_adapter_qybot.adapter import Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

nonebot.load_builtin_plugin("echo")

nonebot.run()