У нас есть самая базовая функция для создания и управления агентами 

# Basic function
`from langchain.agents import create_agent`
```python
def create_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware[StateT_co, ContextT]] = (),
    response_format: ResponseFormat[ResponseT] | type[ResponseT] | dict[str, Any] | None = None,
    state_schema: type[AgentState[ResponseT]] | None = None,
    context_schema: type[ContextT] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache[Any] | None = None,
) 
```

### в кратце

| Параметр           | Что это                                                                                                                                 | Нужно ли нам в MVP?     | Кратко — для чего                                                                |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------- |
| `middleware`       | Последовательность промежуточных обработчиков (hooks), которые могут менять состояние, логировать, добавлять метрики, кэшировать и т.д. | Пока нет                | Логирование, rate-limit, observability, кастомная пред-/пост-обработка           |
| `response_format`  | Ограничение формата ответа модели (JSON, Pydantic, structured output и т.д.)                                                            | Очень желательно        | Заставить модель всегда возвращать код + метаданные в строгом JSON / Pydantic    |
| `state_schema`     | Pydantic-класс, описывающий всю структуру состояния агента (AgentState)                                                                 | Да, важно               | Чтобы состояние было типизировано: messages, код, ошибки, статус проверки и т.д. |
| `context_schema`   | Pydantic-класс для дополнительного контекста (обычно редко используется)                                                                | Скорее нет              | Хранить метаданные сессии, user_id, план и т.п. (если не в state)                |
| `checkpointer`     | Объект для сохранения состояния между шагами (память графа)                                                                             | Да, обязательно         | Чтобы агент мог продолжить работу после паузы, перезапуска, ошибки               |
| `store`            | Хранилище для долгосрочной памяти / файлов / артефактов (VectorStore, SQL, Redis и т.д.)                                                | Позже                   | Сохранение сгенерированных ботов, история генераций, кэш промптов                |
| `interrupt_before` | Список узлов графа, перед которыми делать паузу (human-in-the-loop)                                                                     | Полезно                 | Например: перед запуском кода, перед отправкой в прод, перед финальным ответом   |
| `interrupt_after`  | Список узлов, после которых делать паузу                                                                                                | Полезно                 | После генерации кода, после проверки, после тестов                               |
| `debug`            | Включает подробное логирование шагов графа                                                                                              | Да, на этапе разработки | Видеть, что именно происходит внутри агента                                      |
| `name`             | Имя графа / агента (для логов, Prometheus, LangSmith и т.д.)                                                                            | Да                      | Удобно отличать разные агенты (generator, reviewer, runner и т.д.)               |
| `cache`            | Кэш ответов LLM (in-memory, Redis, SQLite и т.д.)                                                                                       | Очень желательно        | Сильно экономит деньги и время на повторяющихся промптах                         |


---

### Модель
Она принимает модель с которой будет работать наш агент.
```python
agent = create_agent(
    model = "mistral-large-latest"
)
```

---
### tools
Это список функций/инструментов, которые агент может самостоятельно решать вызвать, когда посчитает нужным.

Самый стандартный способ рабоать с tools - через декоратор. Всё это импортируется из `from langchain.tools import tool`

Так же есть и другие способы, которые покачто остануться для нас неизученными 
`StructuredTool.from_function(...)` когда нужен полный контроль

Уже готовый Tool объект, например WikipediaQueryRun, TavilySearch быстрый старт с популярными инструментами

```python
@tool
def search_in_google(query: str) -> str:
    """Ищет информацию в интернете по запросу."""
    # здесь реальная реализация
    return f"Результаты по '{query}': ..."
    
@tool
def generate_bot(описание: str) -> str:
    """Генерирует полный код Telegram-бота по текстовому описанию."""
    # можно даже внутри вызвать другую LLM
    return "from aiogram import ..."
    
tools = [
	search_in_google,
	generate_bot
]
```

`return_direct=True` в @tool → после вызова инструмента агент не думает дальше, а сразу отдаёт результат пользователю


---
### system_prompt

Это инструкция агенту от системы, которая всегда добавляется в начало сообщений перед вызовом модели
- Кто агент (роль)
- Как он должен думать и действовать
- Когда и как использовать инструменты
- В каком стиле отвечать
- Какие правила безопасности / формата соблюдать

| Тип                          | Пример передачи                                                                                      | Когда использовать                              | Поддержка кэширования (Anthropic/Claude) |
| ---------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------- |
| `str`                        | `system_prompt="Ты мастер по aiogram 3. Отвечай только кодом TG-бота."`                              | самый простой и частый случай                   | нет                                      |
| `SystemMessage`              | `from langchain_core.messages import SystemMessage` `system_prompt=SystemMessage(content="Ты...")`   | когда нужна структура (несколько блоков текста) | да (особенно полезно для Claude)         |
| `list[dict]` / сложные блоки | `SystemMessage(content=[{"type": "text", "text": "..."}, {"type": "text", "cache_control": {...}}])` | только для Anthropic с prompt caching           | максимальная                             |

```python
from langchain_core.messages import SystemMessage

SYSTEM_PROMPT = """Ты эксперт по созданию Telegram-ботов на aiogram 3.x.
Твоя единственная задача — по описанию пользователя создать полный, рабочий, безопасный бот.

Правила поведения:
1. Никогда не пиши объяснения вне кода, если пользователь не попросил.
2. Всегда возвращай ТОЛЬКО полный код бота в формате ```python\n<code здесь>\n```
3. Используй современный aiogram 3.x (Router, dp, async/await).
4. Добавляй обработку ошибок, логирование и graceful shutdown.
5. Если нужно что-то уточнить — спроси пользователя, не придумывай.
6. Если задача требует внешних данных (API, БД) — используй соответствующие инструменты.

Доступные инструменты: {tool_names}

Думай шаг за шагом в <thinking>, затем выдавай ToolCall или финальный ответ."""

# Вариант А — просто строка
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT
)

# Вариант Б — с SystemMessage (лучше для Claude/Sonnet)
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SystemMessage(content=SYSTEM_PROMPT)
)
```

---

### response_format
это один из самых важных параметров для нашего MVP.

Он заставляет агента в конце (или в специальном шаге) возвращать **не просто текст**, а **строго структурированные данные**, которые легко парсить и использовать в коде.

Без него агент может выдавать красивый ответ, но потом придётся вручную резать markdown, искать `python` 

| Вариант передачи                        | Что происходит под капотом                                                                           | Поддержка моделей                                   | Когда использовать в нашем проекте                    |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------- |
| `type[BaseModel]` просто класс Pydantic | Автоматически выбирает лучший способ (ProviderStrategy если модель поддерживает, иначе ToolStrategy) | OpenAI, Anthropic, Groq, Mistral (частично), Gemini | ★★★★★ Самый удобный и рекомендуемый старт             |
| `ToolStrategy[MySchema]`                | Принудительно использует **tool calling** (добавляет "fake tool" с нашей схемой)                     | Почти все модели с tool calling                     | Когда нужна 100% гарантия, даже на слабых моделях     |
| `ProviderStrategy[MySchema]`            | Использует **нативный** structured output модели (response_format=..., json_schema и т.д.)           | OpenAI, Anthropic Claude, Gemini                    | Максимальная скорость + экономия токенов              |
| `dict` (JSON Schema)                    | То же, что выше, но в формате чистого JSON Schema                                                    | Те же, что ProviderStrategy                         | Когда не хочешь тянуть Pydantic                       |
| `tuple[str, type[BaseModel]]`           | (доп. промпт, схема) — добавляет инструкцию именно для structured части                              | Почти все                                           | Когда нужно уточнить, как именно заполнять поля схемы |
| `None` (по умолчанию)                   | Обычный текстовый ответ, без структуры                                                               | Все                                                 | Только для отладки / прототипа                        |
#Pydantic — это
==мощная библиотека для Python, которая использует аннотации типов для **валидации данных** и **управления настройками**==, позволяя быстро создавать надежные модели данных, преобразовывать JSON в объекты Python и наоборот, а также проверять соответствие данных заданным схемам, включая сложные вложения и типы. Она значительно упрощает работу с данными, делая код чище, надежнее и быстрее.

```python
from pydantic import BaseModel, Field

class BotGenerationResponse(BaseModel):
    """Финальный структурированный результат генерации бота"""
    full_code: str = Field(..., description="Полный рабочий код бота на aiogram 3.x")
    main_file_name: str = Field("bot.py", description="Как назвать основной файл")
    requirements: list[str] = Field(default_factory=list, description="Список зависимостей в requirements.txt стиле")
    explanation: str | None = Field(None, description="Краткое объяснение, если пользователь попросил")
    potential_issues: list[str] = Field(default_factory=list, description="Возможные проблемы / улучшения")
    status: str = Field(..., description="'success' | 'needs_clarification' | 'error'")
    clarification_questions: list[str] = Field(default_factory=list, description="Вопросы, если нужно уточнить задачу")

# Самый простой и надёжный способ
agent = create_agent(
    model=ChatMistralAI(...),
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    response_format=BotGenerationResponse,          # ← вот так
    # ... остальные параметры
)
```

После выполнения агента получаем:
```python
result = agent.invoke({"messages": [{"role": "user", "content": "Сделай бота, который присылает мем дня"}]})
structured = result["structured_response"]          # ← BotGenerationResponse объект

print(structured.full_code)                         # сразу готовый код
print(structured.requirements)                      # ['aiogram==3.*', 'aiohttp', ...]
```

**state_schema** — это один из самых важных параметров в `create_agent(...)`, если мы хотим сделать надёжный, масштабируемый и отлаживаемый агент.

Кратко и по делу:

### state_schema
Это **Pydantic-класс**, который описывает **всё состояние агента на каждом шаге** выполнения.
Вместо того чтобы хранить просто список сообщений (как в старом create_react_agent), мы говорим системе:
«Вот точная структура данных, которую я хочу видеть в состоянии на протяжении всей работы агента»
Пример того, что нам реально нужно в проекте генератора TG-ботов:
```python
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

class BotGenerationState(BaseModel):
    """Полное состояние агента на любом шаге генерации бота"""
    
    # Основные данные, которые всегда есть
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # Что мы уже сгенерировали
    generated_code: Optional[str] = None
    main_file_name: str = "bot.py"
    requirements_txt: Optional[str] = None
    
    # Результаты проверок
    syntax_ok: bool = False
    lint_ok: bool = False
    review_comments: List[str] = Field(default_factory=list)
    test_results: Optional[str] = None          # вывод pytest / ручных тестов
    runtime_error: Optional[str] = None
    
    # Статус и управление процессом
    status: Literal["planning", "generating", "reviewing", "testing", "fixed", "ready", "needs_clarification", "failed"] = "planning"
    clarification_needed: bool = False
    clarification_questions: List[str] = Field(default_factory=list)
    
    # Метаданные для логов / аналитики
    user_prompt: str = ""
    iteration_count: int = 0
    max_iterations_reached: bool = False
    total_tokens_used: int = 0
```

Зачем это нужно (самые важные причины)

| Причина                              | Почему критично для нашего MVP                              |
|--------------------------------------|-----------------------------------------------------------------|
| Типизация и валидация                | Ошибки ловятся сразу, а не на проде                             |
| Чёткое понимание, на каком шаге мы   | Легко писать условные переходы в графе (if state.status == "reviewing" → ...) |
| Легко сохранять / восстанавливать    | checkpointer просто сериализует этот Pydantic-объект            |
| Отладка и observability              | В LangSmith / логах видно всю картину целиком                   |
| Масштабирование (несколько агентов)  | Один агент генерит → другой ревьюит → третий тестирует → четвёртый деплоит |
| Human-in-the-loop                    | Легко показать пользователю: «вот код, вот проблемы, вот вопросы» |
| Retry / self-correction              | Если status == "failed" → можно автоматически вернуться назад   |

 Как это подключается

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()   # или PostgresSaver, RedisSaver и т.д.

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    response_format=BotGenerationResponse,
    
    state_schema=BotGenerationState,          # ← вот здесь
    checkpointer=checkpointer,
    
    debug=True,
    name="bot-generator-v1",
)
```

После этого каждый вызов `agent.invoke(input)` или `agent.stream(input)` возвращает/пробрасывает состояние именно такого типа.

Самый простой стартовый вариант (если пока не хочется много полей)

```python
class MinimalBotState(BaseModel):
    messages: List[BaseMessage] = Field(default_factory=list)
    generated_code: Optional[str] = None
    status: str = "in_progress"
    error: Optional[str] = None
```

Но чем больше полей вы опишете — тем легче потом будет жить.

### checkpointer
Это **механизм сохранения состояния** (checkpointing / persistence).
Когда агент выполняется, он проходит много шагов: планирование → генерация кода → ревью → исправление → тесты → запуск → ...
**checkpointer** сохраняет **снимок всего состояния** после каждого важного шага (super-step).

Зачем это нужно именно нам:

|Сценарий|Без checkpointer|С checkpointer (MemorySaver / PostgresSaver и т.д.)|
|---|---|---|
|Пользователь закрыл вкладку|Всё потеряно, начинаем заново|Возвращается на тот же шаг, где остановились|
|Код упал на этапе тестов|Приходится генерировать заново|Можно вернуться назад и перезапустить только тесты|
|Human-in-the-loop (пользователь должен одобрить код)|Сложно реализовать паузу|Легко: interrupt → ждём ответа → resume|
|Масштаб (тысячи пользователей)|Всё в памяти сервера → краш при перезапуске|Состояние в PostgreSQL / Redis → перезапуск не страшен|
|Отладка / time-travel|Нет истории|Можно посмотреть любой предыдущий снимок|

Самые частые реализации (от простого к серьёзному):

- `MemorySaver() `→ всё в памяти, идеально для dev / тестов
- `PostgresSaver` / AsyncPostgresSaver → то, что мы хотим в проде (PostgreSQL из стека)
- `RedisSaver` → если нужна очень высокая скорость
- `SqliteSaver` → для локального прототипа

Подключается так:

```python
from langgraph.checkpoint.memory import MemorySaver
# или from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = MemorySaver()   # на старте

graph = create_agent(..., checkpointer=checkpointer, ...)
```

После этого каждый graph.invoke(...) или graph.stream(...) может быть продолжен по thread_id / checkpoint_id.

### graph
LangGraph — это **библиотека для описания сложных агентов как направленного графа** (не линейной цепочки).

Вместо старого подхода:

```
prompt → llm → tool → llm → parser   (линейно, сложно добавить ветвления / циклы)
```

**LangGraph** позволяет:

- **Узлы (nodes)** — отдельные шаги (функции / агенты) Примеры для нас:
    - plan — понять задачу
    - generate_code — сгенерировать код
    - review_code — проверить код
    - fix_bugs — исправить
    - test_bot — запустить тесты
    - run_bot — запустить в sandbox
    - ask_user — спросить уточнение
- **Рёбра (edges)** — правила переходов
    - от generate_code → review_code всегда
    - от review_code → fix_bugs если есть ошибки
    - от review_code → test_bot если всё ок
    - от любого узла → ask_user если нужна информация
- **Состояние (state)** — один общий объект, который передаётся между узлами (тот самый state_schema=BotGenerationState, о котором говорили раньше)
- **Циклы** — нормально, агент может ходить по кругу (генерация → ревью → фикс → ревью …)
- **Условные ветвления** — решают, куда идти дальше, по полю состояния


```python
def route_review(state):
	if state.syntax_ok and not state.review_comments:
            return "test"
	else:
		return "fix"
```

---
###  HumanMessage, AIMessage, SystemMessage
`from langchain.messages import HumanMessage, AIMessage, SystemMessage`
Зачем это нужно:
1. **Чёткое разделение ролей** → модель лучше понимает, кто что говорит (System = инструкция, Human = задача, AI = мой ответ / код)
2. **Поддержка памяти и истории** В state_schema (о котором говорили) поле messages: List[BaseMessage] хранит именно список этих объектов → сохраняется в checkpointer, видно в LangSmith, легко продолжать разговор.
3. **Tool calling и structured output** — AIMessage может содержать tool_calls → это как модель говорит: "вызови инструмент X" После вызова инструмента добавляется ToolMessage → модель видит результат.
4. **Совместимость со всеми провайдерами** Mistral, Claude, GPT, Groq — все ожидают примерно такой же формат: [system] + [human] + [ai] + [human] + ...

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_mistralai import ChatMistralAI

llm = ChatMistralAI(model="mistral-large-latest")

# Начало беседы (это будет в state.messages)
messages = [
    SystemMessage(content="""Ты эксперт по aiogram 3.x.
Отвечай ТОЛЬКО полным рабочим кодом бота в ```python блоке.
Если нужно уточнить — спроси."""),
    
    HumanMessage(content="Сделай бота, который отвечает 'Понг!' на /ping"),
]

# Вызов модели
response = llm.invoke(messages)

# response — это AIMessage
print(response.content)          # → код бота
print(response.tool_calls)       # если модель решила вызвать инструмент

# Добавляем ответ модели в историю (для следующего вызова)
messages.append(response)        # теперь AIMessage в списке

# Следующий запрос пользователя
messages.append(HumanMessage(content="Добавь команду /start с приветствием"))

# Новый вызов — модель уже помнит предыдущий код
new_response = llm.invoke(messages)
```

---

### методы agent

| Метод                                                   | Синхронный / асинхронный | Что делает                                                                    | Зачем нужен в нашем проекте                                                               | Самый частый способ использования                                                   |
| ------------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `.invoke(input, config=None)`                           | sync                     | Запускает граф **до конца** и возвращает **финальное состояние** одним куском | Получить полный результат (код бота + статус + вопросы пользователю и т.д.) за один вызов | `result = agent.invoke({"messages": [HumanMessage(...)], ...})`                     |
| `.ainvoke(input, config=None)`                          | async                    | То же самое, но асинхронно (важно для FastAPI)                                | Основной способ вызова в веб-сервисе / API эндпоинте                                      | `await agent.ainvoke(...)`                                                          |
| `.stream(input, config=None, *, stream_mode="values")`  | sync                     | Стриминг **по шагам графа** — выдаёт кусочки состояния после каждого узла     | Показывать пользователю прогресс: "генерирую код...", "проверяю...", "нашёл ошибку..."    | `for chunk in agent.stream(input, stream_mode="updates"):`                          |
| `.astream(input, config=None, *, stream_mode="values")` | async                    | Асинхронный стриминг (самый важный для реального продукта)                    | Реал-тайм UI в Telegram / веб: токены кода, сообщения о проверке, вопросы пользователю    | `async for chunk in agent.astream(...)`                                             |
| `.get_state(config)`                                    | sync                     | Возвращает **текущее состояние** графа по thread_id / checkpoint_id           | Показать, на каком шаге остановился агент (например, ждёт human approval)                 | `snapshot = agent.get_state(config)`                                                |
| `.aget_state(config)`                                   | async                    | То же, асинхронно                                                             | В API — проверить статус выполнения задачи                                                | `await agent.aget_state(config)`                                                    |
| `.update_state(config, values, as_node=None)`           | sync/async варианты      | **Ручное изменение состояния** (вставить сообщение, поменять статус и т.д.)   | Human-in-the-loop: пользователь ответил на вопрос → вставляем ответ в state.messages      | `agent.update_state(config, {"messages": HumanMessage(...)}, as_node="human_node")` |
| `.astream_events(input, config=None, version="v2")`     | async                    | Очень детальный стриминг событий (on_chat_model_start, on_tool_end и т.д.)    | Отладка, LangSmith-трассировка, кастомные UI с токенами модели в реальном времени         | Используется реже, но мощно для продвинутого мониторинга                            |
| `.get_state_history(config)`                            | sync/async варианты      | История всех чекпоинтов (time-travel)                                         | Отладка: посмотреть, что было в состоянии 3 шага назад                                    | Редко в MVP, но полезно при разработке                                              |

