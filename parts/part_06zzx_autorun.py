# Self-queueing of the next cycle (2026-11-20): /autorun on|off. The workflow reads state/state.json "autorun" and the STOP file before queueing the next cycle.
def autorun_command(c, raw):
    a = c.split()[1:2]
    if a == ["off"]: ST["autorun"] = False; tg("Автозапуск следующего цикла выключен. Текущий цикл дойдёт до конца, потом новый сам не начнётся (расписание раз в час остаётся: чтобы остановить совсем, в GitHub: Actions → agent-cycle → ⋯ → Disable workflow). Включить: /autorun on")
    elif a == ["on"]: ST["autorun"] = True; tg("Автозапуск включён: после каждого цикла следующий встаёт в очередь сам.")
    else: tg("Автозапуск: %s. /autorun on | /autorun off. Файл STOP в репозитории тоже останавливает цепочку." % ("включён" if ST.get("autorun", True) else "выключен"))
EXT_CMDS["/autorun"] = autorun_command
ST.setdefault("autorun", True)
