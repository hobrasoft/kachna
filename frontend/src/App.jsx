import { useEffect, useMemo, useState } from "react";
import { apiClient } from "./apiClient";

const API_URL =
  __KACHNA_API_URL__ ??
  import.meta.env.VITE_API_URL ??
  "http://api.kachna.hobrasoft.cz";

const emptyUser = {
  user: null,
  name: "",
  login: "",
  roles: [],
};

const defaultChatModel = "local-model";

function SectionCard({ title, children }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function LoginForm({ onLogin }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await apiClient.post(API_URL, "/v1/login", {
        login,
        password,
      });

      if (!response.ok) {
        throw new Error("Přihlášení selhalo.");
      }

      const data = await response.json();
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login">
      <div className="login__panel">
        <h1>Kachna</h1>
        <p>Přihlas se do chatu.</p>
        <form className="form" onSubmit={handleSubmit}>
          <label>
            Login
            <input
              type="text"
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              placeholder="např. admin"
              required
            />
          </label>
          <label>
            Heslo
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
            />
          </label>
          {error && <div className="form__error">{error}</div>}
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Ověřuji…" : "Přihlásit"}
          </button>
        </form>
      </div>
    </div>
  );
}

function ChatPanel({ apiUrl, user }) {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [model, setModel] = useState(defaultChatModel);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [editingConversationId, setEditingConversationId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [isSavingConversation, setIsSavingConversation] = useState(false);

  const formatSimilarity = (value) => {
    if (typeof value !== "number") {
      return "";
    }
    return value.toFixed(2);
  };

  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await apiClient.get(apiUrl, "/v1/models");
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        const firstModel = data?.data?.[0]?.id;
        if (firstModel) {
          setModel(firstModel);
        }
      } catch (err) {
        console.error(err);
      }
    };

    loadModels();
  }, [apiUrl]);

  useEffect(() => {
    if (!user?.user) {
      return;
    }

    const loadConversations = async () => {
      setIsLoadingConversations(true);
      try {
        const response = await apiClient.get(
          apiUrl,
          `/v1/users/${user.user}/conversations`,
        );
        if (!response.ok) {
          throw new Error("Nepodařilo se načíst konverzace.");
        }
        const data = await response.json();
        setConversations(data);
        if (!activeConversationId && data.length > 0) {
          setActiveConversationId(data[0].conversation);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoadingConversations(false);
      }
    };

    loadConversations();
  }, [apiUrl, user]);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      setIsLoadingMessages(true);
      try {
        const response = await apiClient.get(
          apiUrl,
          `/v1/conversations/${activeConversationId}/messages`,
        );
        if (!response.ok) {
          throw new Error("Nepodařilo se načíst zprávy.");
        }
        const data = await response.json();
        setMessages(
          data.map((message) => ({
            id: message.message,
            role: message.role,
            content: message.text,
          })),
        );
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoadingMessages(false);
      }
    };

    loadMessages();
  }, [apiUrl, activeConversationId]);

  const handleCreateConversation = async () => {
    if (!user?.user || isLoadingConversations) {
      return;
    }
    setError("");
    setIsLoadingConversations(true);
    try {
      const response = await apiClient.post(
        apiUrl,
        `/v1/users/${user.user}/conversations`,
        { title: "Nová konverzace" },
      );
      if (!response.ok) {
        throw new Error("Konverzaci se nepodařilo založit.");
      }
      const data = await response.json();
      setConversations((prev) => [data, ...prev]);
      setActiveConversationId(data.conversation);
      setMessages([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const handleSelectConversation = (conversationId) => {
    setActiveConversationId(conversationId);
    setError("");
    setOpenMenuId(null);
  };

  const handleOpenConversationMenu = (event, conversationId) => {
    event.stopPropagation();
    setOpenMenuId((prev) => (prev === conversationId ? null : conversationId));
  };

  const handleEditConversation = (event, conversation) => {
    event.stopPropagation();
    setEditingConversationId(conversation.conversation);
    setEditingTitle(conversation.title);
    setOpenMenuId(null);
  };

  const handleCancelEditConversation = (event) => {
    if (event) {
      event.stopPropagation();
    }
    setEditingConversationId(null);
    setEditingTitle("");
  };

  const handleSaveConversationTitle = async (event, conversationId) => {
    event.preventDefault();
    event.stopPropagation();
    if (!user?.user || isSavingConversation) {
      return;
    }
    const trimmedTitle = editingTitle.trim();
    if (!trimmedTitle) {
      setError("Název konverzace nesmí být prázdný.");
      return;
    }
    setError("");
    setIsSavingConversation(true);
    try {
      const response = await apiClient.put(
        apiUrl,
        `/v1/conversations/${conversationId}`,
        { user: user.user, title: trimmedTitle },
      );
      if (!response.ok) {
        throw new Error("Nepodařilo se upravit název konverzace.");
      }
      const data = await response.json();
      setConversations((prev) =>
        prev.map((item) =>
          item.conversation === conversationId ? data : item,
        ),
      );
      setEditingConversationId(null);
      setEditingTitle("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingConversation(false);
    }
  };

  const handleDeleteConversation = async (event, conversationId) => {
    event.stopPropagation();
    if (!user?.user || isSavingConversation) {
      return;
    }
    if (!window.confirm("Opravdu chceš konverzaci smazat?")) {
      return;
    }
    setError("");
    setIsSavingConversation(true);
    try {
      const response = await apiClient.del(
        apiUrl,
        `/v1/conversations/${conversationId}`,
        { user: user.user },
      );
      if (!response.ok) {
        throw new Error("Nepodařilo se odstranit konverzaci.");
      }
      setConversations((prev) => {
        const filtered = prev.filter(
          (item) => item.conversation !== conversationId,
        );
        if (activeConversationId === conversationId) {
          setActiveConversationId(filtered[0]?.conversation ?? null);
          setMessages([]);
        }
        return filtered;
      });
      setOpenMenuId(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingConversation(false);
    }
  };

  const sendMessage = async (question) => {
    if (!question || isLoading || !activeConversationId) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: question }];
    setMessages(nextMessages);
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await apiClient.post(
        apiUrl,
        `/v1/conversations/${activeConversationId}/chat`,
        {
          user: user.user,
          model,
          content: question,
        },
      );

      if (!response.ok) {
        throw new Error("Nepodařilo se získat odpověď.");
      }

      const data = await response.json();
      const reply = data?.assistant_message?.text?.trim();
      if (!reply) {
        throw new Error("Odpověď je prázdná.");
      }
      const matchedFunctions = Array.isArray(data?.matched_functions)
        ? data.matched_functions
        : [];
      const matchedTopics = Array.isArray(data?.matched_topics)
        ? data.matched_topics
        : [];
      const sortBySimilarity = (items, getLabel) =>
        [...items].sort((a, b) => {
          const diff = (b?.similarity ?? 0) - (a?.similarity ?? 0);
          if (diff !== 0) {
            return diff;
          }
          return (getLabel(a) ?? "").localeCompare(getLabel(b) ?? "");
        });
      if (data?.conversation) {
        setConversations((prev) =>
          prev.map((item) =>
            item.conversation === data.conversation.conversation
              ? data.conversation
              : item,
          ),
        );
      }
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: reply,
          matches: {
            functions: sortBySimilarity(matchedFunctions, (item) => item?.name),
            topics: sortBySimilarity(matchedTopics, (item) => item?.text),
          },
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading || !activeConversationId) {
      return;
    }
    await sendMessage(trimmed);
  };

  const handleFunctionQuestionClick = async (match) => {
    if (!match?.first_question) {
      return;
    }
    await sendMessage(match.first_question);
  };

  const visibleMessages = messages.filter((message) => message.role !== "system");

  return (
    <section className="chat-shell">
      <aside className="chat-sidebar">
        <button
          type="button"
          className="chat-sidebar__new"
          onClick={handleCreateConversation}
          disabled={isLoadingConversations}
        >
          {isLoadingConversations ? "Zakládám…" : "Nová konverzace"}
        </button>
        <div
          className="chat-sidebar__list"
          onClick={() => setOpenMenuId(null)}
        >
          {conversations.length === 0 ? (
            <div className="chat-sidebar__empty">Žádné konverzace.</div>
          ) : (
            conversations.map((conversation) => (
              <div
                key={conversation.conversation}
                className={
                  conversation.conversation === activeConversationId
                    ? "chat-sidebar__item active"
                    : "chat-sidebar__item"
                }
                onClick={() =>
                  handleSelectConversation(conversation.conversation)
                }
              >
                {editingConversationId === conversation.conversation ? (
                  <form
                    className="chat-sidebar__edit"
                    onSubmit={(event) =>
                      handleSaveConversationTitle(
                        event,
                        conversation.conversation,
                      )
                    }
                    onClick={(event) => event.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(event) => setEditingTitle(event.target.value)}
                      autoFocus
                    />
                    <div className="chat-sidebar__edit-actions">
                      <button type="submit" disabled={isSavingConversation}>
                        Uložit
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEditConversation}
                      >
                        Zrušit
                      </button>
                    </div>
                  </form>
                ) : (
                  <span className="chat-sidebar__title">
                    {conversation.title}
                  </span>
                )}
                <button
                  type="button"
                  className="chat-sidebar__menu"
                  onClick={(event) =>
                    handleOpenConversationMenu(
                      event,
                      conversation.conversation,
                    )
                  }
                  aria-label="Menu"
                >
                  ⋯
                </button>
                {openMenuId === conversation.conversation && (
                  <div
                    className="chat-sidebar__menu-popup"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={(event) =>
                        handleEditConversation(event, conversation)
                      }
                    >
                      edit
                    </button>
                    <button
                      type="button"
                      onClick={(event) =>
                        handleDeleteConversation(
                          event,
                          conversation.conversation,
                        )
                      }
                    >
                      delete
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </aside>
      <div className="chat">
        <div className="chat__messages">
          {activeConversationId ? (
            visibleMessages.length === 0 && !isLoadingMessages ? (
              <div className="chat__empty">Začni konverzaci.</div>
            ) : (
              visibleMessages.map((message, index) => (
                <div
                  key={`${message.role}-${message.id ?? index}`}
                  className={`chat__message chat__message--${message.role}`}
                >
                  <div className="chat__role">
                    {message.role === "user" ? "Ty" : "Kachna"}
                  </div>
                  <p>{message.content}</p>
                  {message.matches &&
                  (message.matches.functions?.length ||
                    message.matches.topics?.length) ? (
                    <div className="chat__matches">
                      {message.matches.functions?.length ? (
                        <div className="chat__match-group">
                          <div className="chat__match-label">Funkce</div>
                          <ul className="chat__match-list">
                            {message.matches.functions.map((match, matchIndex) => (
                              <li
                                key={`function-${match.function}`}
                                className="chat__match-item"
                              >
                                {matchIndex === 0 || !match.first_question ? (
                                  <span>{match.name}</span>
                                ) : (
                                  <button
                                    type="button"
                                    className="chat__match-button"
                                    onClick={() =>
                                      handleFunctionQuestionClick(match)
                                    }
                                    disabled={isLoading}
                                  >
                                    {match.name}
                                  </button>
                                )}
                                <span className="chat__match-score">
                                  {formatSimilarity(match.similarity)}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {message.matches.topics?.length ? (
                        <div className="chat__match-group">
                          <div className="chat__match-label">Témata</div>
                          <ul className="chat__match-list">
                            {message.matches.topics.map((match) => (
                              <li
                                key={`topic-${match.topic}`}
                                className="chat__match-item"
                              >
                                <span>{match.text}</span>
                                <span className="chat__match-score">
                                  {formatSimilarity(match.similarity)}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))
            )
          ) : (
            <div className="chat__empty">
              Založ novou konverzaci vlevo.
            </div>
          )}
        </div>
        <form className="chat__form" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Napiš zprávu…"
            rows={3}
            disabled={!activeConversationId}
          />
          <div className="chat__actions">
            {error && <span className="chat__error">{error}</span>}
            <button type="submit" disabled={isLoading || !activeConversationId}>
              {isLoading ? "Odesílám…" : "Odeslat"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function UsersSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [error, setError] = useState("");
  const [screen, setScreen] = useState("list");
  const [form, setForm] = useState({
    user: null,
    name: "",
    login: "",
    password: "",
    roles: [],
  });

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/users");
    if (!response.ok) {
      setError("Nepodařilo se načíst uživatele.");
      return;
    }
    const data = await response.json();
    setItems(data);
  };

  const loadRoles = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/user-roles");
    if (!response.ok) {
      setError("Nepodařilo se načíst role.");
      return;
    }
    setAvailableRoles(await response.json());
  };

  useEffect(() => {
    load();
    loadRoles();
  }, [apiUrl]);

  const toggleRoleSelection = (currentRoles, roleId) => {
    const next = new Set(currentRoles ?? []);
    if (next.has(roleId)) {
      next.delete(roleId);
    } else {
      next.add(roleId);
    }
    return Array.from(next);
  };

  const handleCreate = async () => {
    setError("");
    const response = await apiClient.post(apiUrl, "/v1/users", {
      name: form.name,
      login: form.login,
      password: form.password,
      roles: form.roles,
    });
    if (!response.ok) {
      setError("Uživatel se nepodařil vytvořit.");
      return;
    }
    setForm({ user: null, name: "", login: "", password: "", roles: [] });
    setScreen("list");
    await load();
  };

  const handleDelete = async (userId) => {
    const response = await apiClient.del(apiUrl, `/v1/users/${userId}`);
    if (!response.ok) {
      setError("Uživatel se nepodařil odstranit.");
      return;
    }
    if (form.user === userId) {
      setForm({ user: null, name: "", login: "", password: "", roles: [] });
      setScreen("list");
    }
    await load();
  };

  const handleEditSave = async () => {
    if (!form.user) {
      return;
    }
    const payload = {
      name: form.name,
      login: form.login,
      roles: form.roles,
    };
    if (form.password) {
      payload.password = form.password;
    }
    const response = await apiClient.put(
      apiUrl,
      `/v1/users/${form.user}`,
      payload,
    );
    if (!response.ok) {
      setError("Uživatel se nepodařil upravit.");
      return;
    }
    setForm({ user: null, name: "", login: "", password: "", roles: [] });
    setScreen("list");
    await load();
  };

  const handleSave = async (event) => {
    event.preventDefault();
    if (form.user) {
      await handleEditSave();
      return;
    }
    await handleCreate();
  };

  const handleCancel = () => {
    setForm({ user: null, name: "", login: "", password: "", roles: [] });
    setError("");
    setScreen("list");
  };

  const handleAddNew = () => {
    setForm({ user: null, name: "", login: "", password: "", roles: [] });
    setError("");
    setScreen("form");
  };

  const handleEditOpen = (item) => {
    setForm({
      user: item.user,
      name: item.name ?? "",
      login: item.login ?? "",
      password: "",
      roles: (item.roles ?? []).map((role) => role.user_role),
    });
    setError("");
    setScreen("form");
  };

  return (
    <SectionCard title="Správa uživatelů">
      {screen === "list" ? (
        <>
          <button type="button" onClick={handleAddNew}>
            Přidat
          </button>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Jméno</span>
              <span>Login</span>
              <span>Role</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.user}>
                <span>{item.name}</span>
                <span>{item.login}</span>
                <span>
                  {(item.roles ?? [])
                    .map((role) => role.abbr)
                    .join(", ")}
                </span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEditOpen(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <form className="form form--stack" onSubmit={handleSave}>
          <div className="form__row">
            <input
              type="text"
              placeholder="Jméno"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
            <input
              type="text"
              placeholder="Login"
              value={form.login}
              onChange={(event) =>
                setForm({ ...form, login: event.target.value })
              }
              required
            />
          </div>
          <input
            type="password"
            placeholder={form.user ? "Nové heslo (volitelné)" : "Heslo"}
            value={form.password}
            onChange={(event) =>
              setForm({ ...form, password: event.target.value })
            }
            required={!form.user}
          />
          <div className="roles-list">
            {availableRoles.map((role) => (
              <label className="checkbox" key={role.user_role}>
                <input
                  type="checkbox"
                  checked={form.roles.includes(role.user_role)}
                  onChange={() =>
                    setForm((prev) => ({
                      ...prev,
                      roles: toggleRoleSelection(prev.roles, role.user_role),
                    }))
                  }
                />
                {role.abbr} – {role.name}
              </label>
            ))}
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="form__actions">
            <button type="button" onClick={handleCancel}>
              Zrušit
            </button>
            <button type="submit">Uložit</button>
            <button
              type="button"
              onClick={() => handleDelete(form.user)}
              disabled={!form.user}
            >
              Smazat
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}

function RolesSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [form, setForm] = useState({
    user_role: null,
    system_prompt: "",
    abbr: "",
    name: "",
    admin: false,
  });
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const loadRoles = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/user-roles");
    if (!response.ok) {
      setError("Nepodařilo se načíst role.");
      return;
    }
    setItems(await response.json());
  };

  const loadPrompts = async () => {
    const response = await apiClient.get(apiUrl, "/v1/system-prompts");
    if (!response.ok) {
      setError("Nepodařilo se načíst prompty.");
      return;
    }
    setPrompts(await response.json());
  };

  useEffect(() => {
    loadRoles();
    loadPrompts();
  }, [apiUrl]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    const payload = {
      system_prompt: Number(form.system_prompt),
      abbr: form.abbr,
      name: form.name,
      admin: form.admin,
    };
    const response = form.user_role
      ? await apiClient.put(
          apiUrl,
          `/v1/user-roles/${form.user_role}`,
          payload,
        )
      : await apiClient.post(apiUrl, "/v1/user-roles", payload);
    if (!response.ok) {
      setError(
        form.user_role ? "Role se nepodařila upravit." : "Role se nepodařila vytvořit.",
      );
      return;
    }
    setForm({ user_role: null, system_prompt: "", abbr: "", name: "", admin: false });
    setView("list");
    await loadRoles();
  };

  const handleDelete = async () => {
    if (!form.user_role) {
      return;
    }
    const response = await apiClient.del(
      apiUrl,
      `/v1/user-roles/${form.user_role}`,
    );
    if (!response.ok) {
      setError("Role se nepodařila odstranit.");
      return;
    }
    setForm({ user_role: null, system_prompt: "", abbr: "", name: "", admin: false });
    setView("list");
    await loadRoles();
  };

  const handleAdd = () => {
    setError("");
    setForm({ user_role: null, system_prompt: "", abbr: "", name: "", admin: false });
    setView("form");
  };

  const handleEdit = (item) => {
    setError("");
    setForm({
      user_role: item.user_role,
      system_prompt: item.system_prompt ?? "",
      abbr: item.abbr ?? "",
      name: item.name ?? "",
      admin: item.admin ?? false,
    });
    setView("form");
  };

  const handleCancel = () => {
    setError("");
    setForm({ user_role: null, system_prompt: "", abbr: "", name: "", admin: false });
    setView("list");
  };

  const promptName = (promptId) =>
    prompts.find((prompt) => prompt.system_prompt === promptId)?.name ?? "-";

  return (
    <SectionCard title="Správa uživatelských rolí">
      {view === "list" ? (
        <>
          <div className="form__actions">
            <button type="button" onClick={handleAdd}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Prompt</span>
              <span>Zkratka</span>
              <span>Název</span>
              <span>Admin</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.user_role}>
                <span>{promptName(item.system_prompt)}</span>
                <span>{item.abbr}</span>
                <span>{item.name}</span>
                <span>{item.admin ? "Ano" : "Ne"}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <form className="form form--stack" onSubmit={handleSubmit}>
            <label>
              Prompt
              <select
                value={form.system_prompt}
                onChange={(event) =>
                  setForm({ ...form, system_prompt: Number(event.target.value) })
                }
                required
              >
                <option value="" disabled>
                  Vyber prompt
                </option>
                {prompts.map((prompt) => (
                  <option key={prompt.system_prompt} value={prompt.system_prompt}>
                    {prompt.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Zkratka
              <input
                type="text"
                value={form.abbr}
                onChange={(event) => setForm({ ...form, abbr: event.target.value })}
                required
              />
            </label>
            <label>
              Název
              <input
                type="text"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.admin}
                onChange={(event) =>
                  setForm({ ...form, admin: event.target.checked })
                }
              />
              Admin
            </label>
            {error && <div className="form__error">{error}</div>}
            <div className="form__actions">
              <button type="button" onClick={handleCancel}>
                Zrušit
              </button>
              <button type="submit">Uložit</button>
              <button type="button" onClick={handleDelete} disabled={!form.user_role}>
                Smazat
              </button>
            </div>
          </form>
        </>
      )}
    </SectionCard>
  );
}

function SystemPromptsSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    system_prompt: null,
    name: "",
    text: "",
  });
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/system-prompts");
    if (!response.ok) {
      setError("Nepodařilo se načíst prompty.");
      return;
    }
    setItems(await response.json());
  };

  useEffect(() => {
    load();
  }, [apiUrl]);

  const handleAdd = () => {
    setError("");
    setForm({ system_prompt: null, name: "", text: "" });
    setView("form");
  };

  const handleEdit = (item) => {
    setError("");
    setForm({
      system_prompt: item.system_prompt,
      name: item.name ?? "",
      text: item.text ?? "",
    });
    setView("form");
  };

  const handleCancel = () => {
    setError("");
    setForm({ system_prompt: null, name: "", text: "" });
    setView("list");
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const payload = {
      name: form.name,
      text: form.text,
    };
    const response = form.system_prompt
      ? await apiClient.put(
          apiUrl,
          `/v1/system-prompts/${form.system_prompt}`,
          payload,
        )
      : await apiClient.post(apiUrl, "/v1/system-prompts", payload);
    if (!response.ok) {
      setError(
        form.system_prompt
          ? "Prompt se nepodařilo upravit."
          : "Prompt se nepodařilo vytvořit.",
      );
      return;
    }
    await load();
    handleCancel();
  };

  const handleDelete = async () => {
    if (!form.system_prompt) {
      return;
    }
    const response = await apiClient.del(
      apiUrl,
      `/v1/system-prompts/${form.system_prompt}`,
    );
    if (!response.ok) {
      setError("Prompt se nepodařilo odstranit.");
      return;
    }
    await load();
    handleCancel();
  };

  return (
    <SectionCard title="Správa systémových promptů">
      {view === "list" ? (
        <>
          <div className="table__actions">
            <button type="button" onClick={handleAdd}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Název</span>
              <span>Text</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.system_prompt}>
                <span>{item.name}</span>
                <span>{item.text}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <form className="form form--stack" onSubmit={handleSave}>
          <label>
            Název
            <input
              type="text"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
          </label>
          <label>
            Text
            <textarea
              value={form.text}
              onChange={(event) => setForm({ ...form, text: event.target.value })}
              rows={10}
              required
            />
          </label>
          {error && <div className="form__error">{error}</div>}
          <div className="form__actions">
            <button type="button" onClick={handleCancel}>
              Zrušit
            </button>
            <button type="submit">Uložit</button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={!form.system_prompt}
            >
              Smazat
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}

function TopicCategoriesSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [view, setView] = useState("list");
  const [error, setError] = useState("");
  const [policies, setPolicies] = useState([]);

  const formatPolicies = (items) => {
    if (!items || items.length === 0) {
      return "—";
    }
    return items
      .map(
        (policy) =>
          `${policy.role_name} (${policy.role_abbr}): ${policy.policy_name}${
            policy.policy ? ` – ${policy.policy}` : ""
          }`,
      )
      .join(", ");
  };

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/topic-categories");
    if (!response.ok) {
      setError("Nepodařilo se načíst kategorie.");
      return;
    }
    setItems(await response.json());
  };

  useEffect(() => {
    load();
  }, [apiUrl]);

  const startCreate = () => {
    setForm({ name: "", description: "" });
    setEditingId(null);
    setPolicies([]);
    setError("");
    setView("form");
  };

  const startEdit = (item) => {
    setForm({
      name: item.name,
      description: item.description,
    });
    setEditingId(item.topic_category);
    setPolicies(item.policies ?? []);
    setError("");
    setView("form");
  };

  const handleCancel = () => {
    setForm({ name: "", description: "" });
    setEditingId(null);
    setPolicies([]);
    setError("");
    setView("list");
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const response = editingId
      ? await apiClient.put(
          apiUrl,
          `/v1/topic-categories/${editingId}`,
          form,
        )
      : await apiClient.post(apiUrl, "/v1/topic-categories", form);
    if (!response.ok) {
      setError(
        editingId
          ? "Kategorie se nepodařila upravit."
          : "Kategorie se nepodařila vytvořit.",
      );
      return;
    }
    await load();
    handleCancel();
  };

  const handleDelete = async () => {
    if (!editingId) {
      return;
    }
    const response = await apiClient.del(
      apiUrl,
      `/v1/topic-categories/${editingId}`,
    );
    if (!response.ok) {
      setError("Kategorie se nepodařila odstranit.");
      return;
    }
    await load();
    handleCancel();
  };

  return (
    <SectionCard title="Správa kategorií témat">
      {view === "list" ? (
        <>
          <div className="table__actions">
            <button type="button" onClick={startCreate}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Název</span>
              <span>Popis</span>
              <span>Politiky</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.topic_category}>
                <span>{item.name}</span>
                <span>{item.description}</span>
                <span>{formatPolicies(item.policies)}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => startEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <form className="form form--stack" onSubmit={handleSave}>
            {editingId && (
              <div className="form__info">Kód kategorie: {editingId}</div>
            )}
            <div className="form__info">
              Politiky: {formatPolicies(policies)}
            </div>
            <label>
              Název
              <input
                type="text"
                value={form.name}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                required
              />
            </label>
            <label>
              Popis
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm({ ...form, description: event.target.value })
                }
                required
              />
            </label>
            {error && <div className="form__error">{error}</div>}
            <div className="form__actions">
              <button type="button" onClick={handleCancel}>
                Zrušit
              </button>
              <button type="submit">Uložit</button>
              <button type="button" onClick={handleDelete} disabled={!editingId}>
                Smazat
              </button>
            </div>
          </form>
        </>
      )}
    </SectionCard>
  );
}

function TopicsSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    topic_category: "",
    text: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/topics");
    if (!response.ok) {
      setError("Nepodařilo se načíst témata.");
      return;
    }
    setItems(await response.json());
  };

  const loadCategories = async () => {
    const response = await apiClient.get(apiUrl, "/v1/topic-categories");
    if (!response.ok) {
      return;
    }
    setCategories(await response.json());
  };

  useEffect(() => {
    load();
    loadCategories();
  }, [apiUrl]);

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const topicCategoryValue = Number(form.topic_category);
    if (!Number.isInteger(topicCategoryValue)) {
      setError("Kategorie musí být číslo.");
      return;
    }
    const payload = {
      topic_category: topicCategoryValue,
      text: form.text,
    };
    const response = editingId
      ? await apiClient.put(apiUrl, `/v1/topics/${editingId}`, payload)
      : await apiClient.post(apiUrl, "/v1/topics", payload);
    if (!response.ok) {
      setError(
        editingId
          ? "Téma se nepodařilo upravit."
          : "Téma se nepodařilo vytvořit.",
      );
      return;
    }
    setForm({ topic_category: "", text: "" });
    setEditingId(null);
    setView("list");
    await load();
  };

  const handleDelete = async () => {
    if (!editingId) {
      return;
    }
    const response = await apiClient.del(apiUrl, `/v1/topics/${editingId}`);
    if (!response.ok) {
      setError("Téma se nepodařilo odstranit.");
      return;
    }
    setForm({ topic_category: "", text: "" });
    setEditingId(null);
    setView("list");
    await load();
  };

  const handleCancel = () => {
    setForm({ topic_category: "", text: "" });
    setEditingId(null);
    setError("");
    setView("list");
  };

  const handleAdd = () => {
    setForm({ topic_category: "", text: "" });
    setEditingId(null);
    setError("");
    setView("form");
  };

  const handleEdit = (item) => {
    setForm({
      topic_category: item.topic_category ?? "",
      text: item.text ?? "",
    });
    setEditingId(item.topic);
    setError("");
    setView("form");
  };

  return (
    <SectionCard title="Správa témat">
      {view === "list" ? (
        <>
          <div className="table__actions">
            <button type="button" onClick={handleAdd}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>ID</span>
              <span>Kategorie</span>
              <span>Text</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.topic}>
                <span>{item.topic}</span>
                <span>
                  {categories.find(
                    (category) => category.topic_category === item.topic_category,
                  )?.name ?? item.topic_category}
                </span>
                <span>{item.text}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <form className="form form--stack" onSubmit={handleSave}>
          {editingId && <div className="form__info">ID tématu: {editingId}</div>}
          <label>
            Kategorie
            <select
              value={form.topic_category}
              onChange={(event) =>
                setForm({ ...form, topic_category: event.target.value })
              }
              required
            >
              <option value="">Vyberte kategorii</option>
              {categories.map((category) => (
                <option
                  key={category.topic_category}
                  value={category.topic_category}
                >
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Text tématu
            <textarea
              value={form.text}
              onChange={(event) =>
                setForm({ ...form, text: event.target.value })
              }
              required
            />
          </label>
          {error && <div className="form__error">{error}</div>}
          <div className="form__actions">
            <button type="button" onClick={handleCancel}>
              Zrušit
            </button>
            <button type="submit">Uložit</button>
            <button type="button" onClick={handleDelete} disabled={!editingId}>
              Smazat
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}

function FunctionQuestionsSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [functions, setFunctions] = useState([]);
  const [form, setForm] = useState({
    function_question: null,
    function: "",
    text: "",
  });
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/function-questions");
    if (!response.ok) {
      setError("Nepodařilo se načíst dotazy k funkcím.");
      return;
    }
    setItems(await response.json());
  };

  const loadFunctions = async () => {
    const response = await apiClient.get(apiUrl, "/v1/functions");
    if (!response.ok) {
      setError("Nepodařilo se načíst funkce.");
      return;
    }
    setFunctions(await response.json());
  };

  useEffect(() => {
    load();
    loadFunctions();
  }, [apiUrl]);

  const handleAdd = () => {
    setError("");
    setForm({ function_question: null, function: "", text: "" });
    setView("form");
  };

  const handleEdit = (item) => {
    setError("");
    setForm({
      function_question: item.function_question,
      function: item.function ?? "",
      text: item.text ?? "",
    });
    setView("form");
  };

  const handleCancel = () => {
    setError("");
    setForm({ function_question: null, function: "", text: "" });
    setView("list");
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const payload = {
      function: Number(form.function),
      text: form.text,
    };
    const response = form.function_question
      ? await apiClient.put(
          apiUrl,
          `/v1/function-questions/${form.function_question}`,
          payload,
        )
      : await apiClient.post(apiUrl, "/v1/function-questions", payload);
    if (!response.ok) {
      setError(
        form.function_question
          ? "Dotaz k funkci se nepodařilo upravit."
          : "Dotaz k funkci se nepodařilo vytvořit.",
      );
      return;
    }
    await load();
    handleCancel();
  };

  const handleDelete = async () => {
    if (!form.function_question) {
      return;
    }
    const response = await apiClient.del(
      apiUrl,
      `/v1/function-questions/${form.function_question}`,
    );
    if (!response.ok) {
      setError("Dotaz k funkci se nepodařilo odstranit.");
      return;
    }
    await load();
    handleCancel();
  };

  const functionName = (functionId) =>
    functions.find((item) => item.function === functionId)?.name ?? "-";

  return (
    <SectionCard title="Dotazy k funkcím">
      {view === "list" ? (
        <>
          <div className="table__actions">
            <button type="button" onClick={handleAdd}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Funkce</span>
              <span>Text dotazu</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.function_question}>
                <span>{functionName(item.function)}</span>
                <span>{item.text}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <form className="form form--stack" onSubmit={handleSave}>
          <label>
            Funkce
            <select
              value={form.function}
              onChange={(event) =>
                setForm({ ...form, function: event.target.value })
              }
              required
            >
              <option value="" disabled>
                Vyber funkci
              </option>
              {functions.map((item) => (
                <option key={item.function} value={item.function}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Text dotazu
            <textarea
              value={form.text}
              onChange={(event) => setForm({ ...form, text: event.target.value })}
              required
            />
          </label>
          {error && <div className="form__error">{error}</div>}
          <div className="form__actions">
            <button type="button" onClick={handleCancel}>
              Zrušit
            </button>
            <button type="submit">Uložit</button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={!form.function_question}
            >
              Smazat
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}

function FunctionsSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [form, setForm] = useState({
    function: null,
    name: "",
    description: "",
    type: "",
    script: "",
    active: true,
    user_roles: [],
  });
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const toggleRoleSelection = (currentRoles, roleId) => {
    const next = new Set(currentRoles ?? []);
    if (next.has(roleId)) {
      next.delete(roleId);
    } else {
      next.add(roleId);
    }
    return Array.from(next);
  };

  const resetForm = () =>
    setForm({
      function: null,
      name: "",
      description: "",
      type: "",
      script: "",
      active: true,
      user_roles: [],
    });

  const load = async () => {
    setError("");
    const response = await apiClient.get(apiUrl, "/v1/functions");
    if (!response.ok) {
      setError("Nepodařilo se načíst funkce.");
      return;
    }
    setItems(await response.json());
  };

  const loadRoles = async () => {
    const response = await apiClient.get(apiUrl, "/v1/user-roles");
    if (!response.ok) {
      setError("Nepodařilo se načíst role.");
      return;
    }
    setAvailableRoles(await response.json());
  };

  useEffect(() => {
    load();
    loadRoles();
  }, [apiUrl]);

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const payload = {
      name: form.name,
      description: form.description,
      type: form.type,
      script: form.script,
      active: form.active,
      user_roles: form.user_roles,
    };
    const response = form.function
      ? await apiClient.put(
          apiUrl,
          `/v1/functions/${form.function}`,
          payload,
        )
      : await apiClient.post(apiUrl, "/v1/functions", payload);
    if (!response.ok) {
      setError(
        form.function
          ? "Funkci se nepodařilo upravit."
          : "Funkci se nepodařilo vytvořit.",
      );
      return;
    }
    resetForm();
    setView("list");
    await load();
  };

  const handleDelete = async () => {
    if (!form.function) {
      return;
    }
    const response = await apiClient.del(
      apiUrl,
      `/v1/functions/${form.function}`,
    );
    if (!response.ok) {
      setError("Funkci se nepodařilo odstranit.");
      return;
    }
    resetForm();
    setView("list");
    await load();
  };

  const handleAdd = () => {
    setError("");
    resetForm();
    setView("form");
  };

  const handleEdit = (item) => {
    setError("");
    setForm({
      function: item.function,
      name: item.name ?? "",
      description: item.description ?? "",
      type: item.type ?? "",
      script: item.script ?? "",
      active: item.active ?? false,
      user_roles: item.user_roles ?? [],
    });
    setView("form");
  };

  const handleCancel = () => {
    setError("");
    resetForm();
    setView("list");
  };

  return (
    <SectionCard title="Správa funkcí">
      {view === "list" ? (
        <>
          <div className="table__actions">
            <button type="button" onClick={handleAdd}>
              Přidat
            </button>
          </div>
          {error && <div className="form__error">{error}</div>}
          <div className="table">
            <div className="table__row table__head">
              <span>Název</span>
              <span>Role</span>
              <span>Typ</span>
              <span>Aktivní</span>
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.function}>
                <span>{item.name}</span>
                <span>{(item.role_abbrs ?? []).join(", ") || "-"}</span>
                <span>{item.type}</span>
                <span>{item.active ? "Ano" : "Ne"}</span>
                <div className="table__actions">
                  <button type="button" onClick={() => handleEdit(item)}>
                    Upravit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <form className="form form--stack" onSubmit={handleSave}>
          <div className="form__row">
            <input
              type="text"
              placeholder="Název"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
            <input
              type="text"
              placeholder="Typ"
              value={form.type}
              onChange={(event) => setForm({ ...form, type: event.target.value })}
              required
            />
          </div>
          <div className="roles-list">
            {availableRoles.map((role) => (
              <label className="checkbox" key={role.user_role}>
                <input
                  type="checkbox"
                  checked={form.user_roles.includes(role.user_role)}
                  onChange={() =>
                    setForm((prev) => ({
                      ...prev,
                      user_roles: toggleRoleSelection(prev.user_roles, role.user_role),
                    }))
                  }
                />
                {role.abbr} – {role.name}
              </label>
            ))}
          </div>
          <textarea
            placeholder="Popis"
            value={form.description}
            onChange={(event) =>
              setForm({ ...form, description: event.target.value })
            }
            required
          />
          <textarea
            placeholder="Skript"
            value={form.script}
            onChange={(event) =>
              setForm({ ...form, script: event.target.value })
            }
            required
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(event) =>
                setForm({ ...form, active: event.target.checked })
              }
            />
            Aktivní
          </label>
          {error && <div className="form__error">{error}</div>}
          <div className="form__actions">
            <button type="button" onClick={handleCancel}>
              Zrušit
            </button>
            <button type="submit">Uložit</button>
            <button type="button" onClick={handleDelete} disabled={!form.function}>
              Smazat
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}

function AdminPanel({ apiUrl }) {
  const sections = useMemo(
    () => [
      { key: "users", label: "Uživatelé", component: UsersSection },
      { key: "roles", label: "Role", component: RolesSection },
      { key: "system-prompts", label: "Prompty", component: SystemPromptsSection },
      { key: "topics", label: "Témata", component: TopicsSection },
      { key: "topic-categories", label: "Kategorie", component: TopicCategoriesSection },
      { key: "function-questions", label: "Dotazy k funkcím", component: FunctionQuestionsSection },
      { key: "functions", label: "Funkce", component: FunctionsSection },
    ],
    [],
  );
  const [activeKey, setActiveKey] = useState(sections[0].key);
  const activeSection = sections.find((section) => section.key === activeKey);

  return (
    <div className="app__body">
      <nav className="tabs">
        {sections.map((section) => (
          <button
            key={section.key}
            type="button"
            className={section.key === activeKey ? "active" : ""}
            onClick={() => setActiveKey(section.key)}
          >
            {section.label}
          </button>
        ))}
      </nav>
      <main className="content">
        {activeSection && (
          <activeSection.component apiUrl={apiUrl} />
        )}
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(emptyUser);
  const [activeView, setActiveView] = useState("chat");

  const hasAdminAccess = user.roles?.some((role) => role.admin);

  const handleLogin = (data) => {
    setUser(data);
    setActiveView("chat");
  };

  const handleLogout = () => {
    setUser(emptyUser);
    setActiveView("chat");
  };

  return user.user ? (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          <h1>Kachna</h1>
          <div className="app__nav">
            <button
              type="button"
              className={activeView === "chat" ? "active" : ""}
              onClick={() => setActiveView("chat")}
            >
              Chat
            </button>
            {hasAdminAccess && (
              <button
                type="button"
                className={activeView === "admin" ? "active" : ""}
                onClick={() => setActiveView("admin")}
              >
                Administrace
              </button>
            )}
          </div>
        </div>
        <div className="app__user">
          <span>
            {user.name} ({user.login})
          </span>
          <button type="button" onClick={handleLogout}>
            Odhlásit
          </button>
        </div>
      </header>
      {activeView === "admin" && hasAdminAccess ? (
        <AdminPanel apiUrl={API_URL} />
      ) : (
        <main className="content content--chat">
          <ChatPanel apiUrl={API_URL} user={user} />
        </main>
      )}
    </div>
  ) : (
    <LoginForm onLogin={handleLogin} />
  );
}
