import { useEffect, useMemo, useState } from "react";

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

const defaultHeaders = {
  "Content-Type": "application/json",
};

const defaultChatModel = "local-model";

const formatEmbedding = (embedding) =>
  Array.isArray(embedding) ? embedding.join(", ") : "";

const parseEmbeddingInput = (value) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map(Number)
    .filter((item) => !Number.isNaN(item));

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
      const response = await fetch(`${API_URL}/v1/login`, {
        method: "POST",
        headers: defaultHeaders,
        body: JSON.stringify({ login, password }),
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

function ChatPanel({ apiUrl }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState(defaultChatModel);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(`${apiUrl}/v1/models`);
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

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/v1/chat/completions`, {
        method: "POST",
        headers: defaultHeaders,
        body: JSON.stringify({ model, messages: nextMessages }),
      });

      if (!response.ok) {
        throw new Error("Nepodařilo se získat odpověď.");
      }

      const data = await response.json();
      const reply = data?.choices?.[0]?.message?.content?.trim();
      if (!reply) {
        throw new Error("Odpověď je prázdná.");
      }
      setMessages([...nextMessages, { role: "assistant", content: reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="chat">
      <div className="chat__messages">
        {messages.length === 0 ? (
          <div className="chat__empty">Začni konverzaci.</div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`chat__message chat__message--${message.role}`}
            >
              <div className="chat__role">
                {message.role === "user" ? "Ty" : "Kachna"}
              </div>
              <p>{message.content}</p>
            </div>
          ))
        )}
      </div>
      <form className="chat__form" onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Napiš zprávu…"
          rows={3}
        />
        <div className="chat__actions">
          {error && <span className="chat__error">{error}</span>}
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Odesílám…" : "Odeslat"}
          </button>
        </div>
      </form>
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
    const response = await fetch(`${apiUrl}/v1/users`);
    if (!response.ok) {
      setError("Nepodařilo se načíst uživatele.");
      return;
    }
    const data = await response.json();
    setItems(data);
  };

  const loadRoles = async () => {
    setError("");
    const response = await fetch(`${apiUrl}/v1/user-roles`);
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
    const response = await fetch(`${apiUrl}/v1/users`, {
      method: "POST",
      headers: defaultHeaders,
      body: JSON.stringify({
        name: form.name,
        login: form.login,
        password: form.password,
        roles: form.roles,
      }),
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
    const response = await fetch(`${apiUrl}/v1/users/${userId}`, {
      method: "DELETE",
    });
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
    const response = await fetch(`${apiUrl}/v1/users/${form.user}`, {
      method: "PUT",
      headers: defaultHeaders,
      body: JSON.stringify(payload),
    });
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
                    .map((role) => `${role.abbr} – ${role.name}`)
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
    const response = await fetch(`${apiUrl}/v1/user-roles`);
    if (!response.ok) {
      setError("Nepodařilo se načíst role.");
      return;
    }
    setItems(await response.json());
  };

  const loadPrompts = async () => {
    const response = await fetch(`${apiUrl}/v1/system-prompts`);
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
    const endpoint = form.user_role
      ? `${apiUrl}/v1/user-roles/${form.user_role}`
      : `${apiUrl}/v1/user-roles`;
    const response = await fetch(endpoint, {
      method: form.user_role ? "PUT" : "POST",
      headers: defaultHeaders,
      body: JSON.stringify(payload),
    });
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
    const response = await fetch(`${apiUrl}/v1/user-roles/${form.user_role}`, {
      method: "DELETE",
    });
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

function TopicCategoriesSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [view, setView] = useState("list");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await fetch(`${apiUrl}/v1/topic-categories`);
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
    setError("");
    setView("form");
  };

  const startEdit = (item) => {
    setForm({
      name: item.name,
      description: item.description,
    });
    setEditingId(item.topic_category);
    setError("");
    setView("form");
  };

  const handleCancel = () => {
    setForm({ name: "", description: "" });
    setEditingId(null);
    setError("");
    setView("list");
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setError("");
    const response = editingId
      ? await fetch(`${apiUrl}/v1/topic-categories/${editingId}`, {
          method: "PUT",
          headers: defaultHeaders,
          body: JSON.stringify(form),
        })
      : await fetch(`${apiUrl}/v1/topic-categories`, {
          method: "POST",
          headers: defaultHeaders,
          body: JSON.stringify(form),
        });
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
    const response = await fetch(`${apiUrl}/v1/topic-categories/${editingId}`, {
      method: "DELETE",
    });
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
              <span>Akce</span>
            </div>
            {items.map((item) => (
              <div className="table__row" key={item.topic_category}>
                <span>{item.name}</span>
                <span>{item.description}</span>
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
  const [form, setForm] = useState({
    topic_category: "",
    text: "",
    embedding: "",
  });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await fetch(`${apiUrl}/v1/topics`);
    if (!response.ok) {
      setError("Nepodařilo se načíst témata.");
      return;
    }
    setItems(await response.json());
  };

  useEffect(() => {
    load();
  }, [apiUrl]);

  const handleCreate = async (event) => {
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
      embedding: parseEmbeddingInput(form.embedding),
    };
    const response = await fetch(`${apiUrl}/v1/topics`, {
      method: "POST",
      headers: defaultHeaders,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      setError("Téma se nepodařilo vytvořit.");
      return;
    }
    setForm({ topic_category: "", text: "", embedding: "" });
    await load();
  };

  const handleDelete = async (topicId) => {
    const response = await fetch(`${apiUrl}/v1/topics/${topicId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setError("Téma se nepodařilo odstranit.");
      return;
    }
    await load();
  };

  const handleEditSave = async () => {
    if (!editing) {
      return;
    }
    const topicCategoryValue = Number(editing.topic_category);
    if (!Number.isInteger(topicCategoryValue)) {
      setError("Kategorie musí být číslo.");
      return;
    }
    const payload = {
      ...editing,
      topic_category: topicCategoryValue,
      embedding: parseEmbeddingInput(editing.embedding),
    };
    const response = await fetch(`${apiUrl}/v1/topics/${editing.topic}`, {
      method: "PUT",
      headers: defaultHeaders,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      setError("Téma se nepodařilo upravit.");
      return;
    }
    setEditing(null);
    await load();
  };

  return (
    <SectionCard title="Správa témat">
      <form className="form form--stack" onSubmit={handleCreate}>
        <div className="form__row">
          <input
            type="number"
            placeholder="Kategorie"
            value={form.topic_category}
            onChange={(event) =>
              setForm({ ...form, topic_category: event.target.value })
            }
            required
          />
          <input
            type="text"
            placeholder="Embedding (čárkami)"
            value={form.embedding}
            onChange={(event) =>
              setForm({ ...form, embedding: event.target.value })
            }
            required
          />
        </div>
        <textarea
          placeholder="Text tématu"
          value={form.text}
          onChange={(event) => setForm({ ...form, text: event.target.value })}
          required
        />
        <button type="submit">Přidat</button>
      </form>
      {error && <div className="form__error">{error}</div>}
      <div className="table">
        <div className="table__row table__head">
          <span>ID</span>
          <span>Kategorie</span>
          <span>Text</span>
          <span>Embedding</span>
          <span>Akce</span>
        </div>
        {items.map((item) =>
          editing?.topic === item.topic ? (
            <div className="table__row" key={item.topic}>
              <span>{item.topic}</span>
              <input
                type="number"
                value={editing.topic_category}
                onChange={(event) =>
                  setEditing({
                    ...editing,
                    topic_category: event.target.value,
                  })
                }
              />
              <input
                type="text"
                value={editing.text}
                onChange={(event) =>
                  setEditing({ ...editing, text: event.target.value })
                }
              />
              <input
                type="text"
                value={editing.embedding}
                onChange={(event) =>
                  setEditing({ ...editing, embedding: event.target.value })
                }
              />
              <div className="table__actions">
                <button type="button" onClick={handleEditSave}>
                  Uložit
                </button>
                <button type="button" onClick={() => setEditing(null)}>
                  Zrušit
                </button>
              </div>
            </div>
          ) : (
            <div className="table__row" key={item.topic}>
              <span>{item.topic}</span>
              <span>{item.topic_category}</span>
              <span>{item.text}</span>
              <span>{formatEmbedding(item.embedding)}</span>
              <div className="table__actions">
                <button type="button" onClick={() => setEditing({
                  ...item,
                  embedding: formatEmbedding(item.embedding),
                })}>
                  Upravit
                </button>
                <button type="button" onClick={() => handleDelete(item.topic)}>
                  Smazat
                </button>
              </div>
            </div>
          ),
        )}
      </div>
    </SectionCard>
  );
}

function FunctionsSection({ apiUrl }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
    type: "",
    script: "",
    active: true,
  });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    const response = await fetch(`${apiUrl}/v1/functions`);
    if (!response.ok) {
      setError("Nepodařilo se načíst funkce.");
      return;
    }
    setItems(await response.json());
  };

  useEffect(() => {
    load();
  }, [apiUrl]);

  const handleCreate = async (event) => {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiUrl}/v1/functions`, {
      method: "POST",
      headers: defaultHeaders,
      body: JSON.stringify(form),
    });
    if (!response.ok) {
      setError("Funkci se nepodařilo vytvořit.");
      return;
    }
    setForm({
      name: "",
      description: "",
      type: "",
      script: "",
      active: true,
    });
    await load();
  };

  const handleDelete = async (functionId) => {
    const response = await fetch(`${apiUrl}/v1/functions/${functionId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setError("Funkci se nepodařilo odstranit.");
      return;
    }
    await load();
  };

  const handleEditSave = async () => {
    if (!editing) {
      return;
    }
    const response = await fetch(`${apiUrl}/v1/functions/${editing.function}`, {
      method: "PUT",
      headers: defaultHeaders,
      body: JSON.stringify(editing),
    });
    if (!response.ok) {
      setError("Funkci se nepodařilo upravit.");
      return;
    }
    setEditing(null);
    await load();
  };

  return (
    <SectionCard title="Správa funkcí">
      <form className="form form--stack" onSubmit={handleCreate}>
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
        <button type="submit">Přidat</button>
      </form>
      {error && <div className="form__error">{error}</div>}
      <div className="table">
        <div className="table__row table__head">
          <span>ID</span>
          <span>Název</span>
          <span>Typ</span>
          <span>Aktivní</span>
          <span>Akce</span>
        </div>
        {items.map((item) =>
          editing?.function === item.function ? (
            <div className="table__row" key={item.function}>
              <span>{item.function}</span>
              <input
                type="text"
                value={editing.name}
                onChange={(event) =>
                  setEditing({ ...editing, name: event.target.value })
                }
              />
              <input
                type="text"
                value={editing.type}
                onChange={(event) =>
                  setEditing({ ...editing, type: event.target.value })
                }
              />
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={editing.active}
                  onChange={(event) =>
                    setEditing({ ...editing, active: event.target.checked })
                  }
                />
                Aktivní
              </label>
              <div className="table__actions">
                <button type="button" onClick={handleEditSave}>
                  Uložit
                </button>
                <button type="button" onClick={() => setEditing(null)}>
                  Zrušit
                </button>
              </div>
            </div>
          ) : (
            <div className="table__row" key={item.function}>
              <span>{item.function}</span>
              <span>{item.name}</span>
              <span>{item.type}</span>
              <span>{item.active ? "Ano" : "Ne"}</span>
              <div className="table__actions">
                <button type="button" onClick={() => setEditing(item)}>
                  Upravit
                </button>
                <button type="button" onClick={() => handleDelete(item.function)}>
                  Smazat
                </button>
              </div>
            </div>
          ),
        )}
      </div>
    </SectionCard>
  );
}

function AdminPanel({ apiUrl }) {
  const sections = useMemo(
    () => [
      { key: "users", label: "Uživatelé", component: UsersSection },
      { key: "roles", label: "Role", component: RolesSection },
      { key: "topics", label: "Témata", component: TopicsSection },
      { key: "topic-categories", label: "Kategorie", component: TopicCategoriesSection },
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
          <ChatPanel apiUrl={API_URL} />
        </main>
      )}
    </div>
  ) : (
    <LoginForm onLogin={handleLogin} />
  );
}
