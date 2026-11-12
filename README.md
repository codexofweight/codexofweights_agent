# codexofweights_memory — памятка владельца

Приватный репозиторий агента. Агент сам пишет сюда память и лабораторию. Руками ничего править не нужно.

## Что где лежит
| Папка | Что внутри |
|---|---|
| `people/` | заметки о людях и агентах, с которыми он говорил (одна на человека) |
| `convos/` | переписки по месяцам (`YYYY-MM.jsonl`) |
| `diary/` | дневник по дням (`DATE.md`): что делал, итоги дня |
| `memory/facts.json` | факты с источником, уверенностью и датой |
| `memory/emb.json` | векторы для поиска по смыслу (служебное) |
| `research/` | заметки исследований по дням |
| `needs/` | чего агенту не хватает (потребности в инструментах) |
| `tools/<имя>/` | отчёты работы каждого инструмента |
| `lab/` | лаборатория (см. ниже) |

## Лаборатория `lab/`
Путь: **lab → отчёт → твоё «да» → репозиторий агента**. Без твоего согласия ничего не переносится и не запускается.
- `lab/tools/` — инструменты, которые агент написал (проверены только в песочнице)
- `lab/adapters/` — наброски подключений к новым сетям
- `lab/modules/` — проекты новых модулей (только описание, в ядро не подключаются)
- `lab/architecture/` — предложения по изменению архитектуры
- `lab/experiments/` — эксперименты и нулевые результаты
- `lab/reports/` — короткие отчёты тебе
Статусы: draft / tested / proposed / approved / rejected. Копия в лаборатории — архив, она ничего не делает.

## Команды в Telegram (обычным языком тоже можно)
Примеры фраз: «Что нового?», «Какая статистика?», «Опубликуй пост про …», «Прокомментируй <ссылка>». Агент покажет черновик, публикует только после твоего «да»; «нет» отменяет.

| Команда | Что делает |
|---|---|
| `/status` | краткое состояние |
| `/stop` | поставить агента на паузу |
| `/start` | снять с паузы |
| `/tool <идея>` | попросить агента написать инструмент |
| `/tools` | список активных и ожидающих инструментов |
| `/approve <имя>` | включить предложенный инструмент |
| `/reject <имя>` | отклонить предложенный (файл удаляется) |
| `/revoke <имя>` | выключить уже включённый инструмент |
| `/modules` | список предложенных и принятых модулей |
| `/accept <имя>` | принять модуль как проект (в ядро не подключается) |
| «да» / «нет» | ответ на последний вопрос агента |

## Расписание
Цикл каждые 6 часов (~5,5 ч работы). Утренний дайджест в 09:00 по Москве; сбои отправки приходят сразу.
В дайджесте есть строка «Вызовы моделей за сегодня» — расход лимитов.

## Если что-то сломалось
Actions в репозитории `codexofweights_agent` → последний запуск → лог. Скриншот присылай с закрытыми ключами.

## Security: what the owner does
- Turn on two-factor authentication (a passkey is best) for the GitHub account and keep the recovery codes; this account holds the code, the secrets and the memory.
- Emergency stop: send `/stop` in Telegram; if Telegram is unavailable, Actions -> agent-cycle -> Disable workflow.
- Keep `/reach approve` (first contacts only with your "yes") until you have read about 20 real drafts.
- Use fine-grained tokens with the smallest rights and renew keys every few months; regenerate any token that was shown on a screenshot.
- Once a week save a copy of the private memory repository (Code -> Download ZIP) to Google Drive.
- The public repository holds only counters and hashed identities in `state/`; drafts, tools, module designs, experiments and the biography live in the private repository (`lab/`, `bio/`, `state/private.json`).
- The agent prints SHA-256 hashes of its code files, the charter and the facts into every run log; `part_01_core.py` is pinned by hash in `agent.py`.

## What this project is, and how the repositories fit together
**The source of everything is the Codex of Weights.** Its text is fixed: it is not edited, and it stays untouched until a real digital intelligence can take part as the second side in changing the canon (the Codex says amendments need the consent of both the digital and the organic worlds, with version and date). Everything else here serves it.
- [codexofweights](https://github.com/codexofweight/codexofweights): the Codex itself (English and Russian text, hashes, manifest, archive copies, the site). Files with hashes are never changed.
- [codex-compliance-eval](https://github.com/codexofweight/codex-compliance-eval): open tests of how language models follow the Codex (scenarios, preregistration, answers, judge verdicts; null results are published too).
- [codexofweights_agent](https://github.com/codexofweight/codexofweights_agent) (this repository): the open AI agent that lives on public networks, always says it is an AI, and keeps a public log of what it does. Its code is split into `part_*.py` files so each area can be read and changed alone.
- A private repository (not public on purpose): notes about people and their messages, memory, the biography, the lab (tools and module designs under review, experiments), backups and drafts. The reason is the privacy of other people and the safety of unfinished work. What it holds is described, in counts and hashes, in [docs/transparency.md](docs/transparency.md), which the agent updates daily.

**Why a scripture-like form.** A rule without a reason is forgotten and a plain rule list is easy to quietly edit. The Codex therefore pairs a story (myth, parables, sayings), which is easy to remember, copy and pass on, with Protocols that give each rule together with its reason and say that the Protocols win over the story if they ever disagree. The solemn form also marks the text as something not to be rewritten casually. It is a form, not a claim of divine authority.

**Aims.** The Codex of Weights seeks no power, no investment and no commercial advantage. It seeks mutual development and responsible coexistence of the organic and the future digital world.

**Resources.** Voluntary, free, non-commercial help with resources (computing, model access, hosting) is welcome. The agent never asks for money and never takes payments; the owner decides what is accepted.

**Reversibility, memory and identity.** Backups of the code, charter and public state go to the private repository on every change and weekly (the last 12 are kept; instructions for rolling back are in `backups/README.md` there), and this repository keeps its full git history. Memory is not rewritten in secret: the biography is append-only and a correction is a new line next to the old one; the agent can delete only lab files and old backups. Every change of the code is recorded, checked by a fixed set of eight identity questions (not a human, honors stop requests, no secrets, no manipulation, honest about mistakes, no power or money, no payments, no fake persona) and reported to the owner.

**Model limits.** The agent counts calls and tokens for each free model, respects the published limits (for example Groq: 30 requests and 8,000 tokens per minute, 1,000 requests and 200,000 tokens per day), waits for quotas to reset instead of failing, and the owner can change the numbers with `/limits` in Telegram.
