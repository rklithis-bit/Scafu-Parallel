(() => {
  const form = document.querySelector("#auth-form");
  const signinTab = document.querySelector("#signin-tab");
  const signupTab = document.querySelector("#signup-tab");
  const usernameWrap = document.querySelector("#username-wrap");
  const username = document.querySelector("#username");
  const email = document.querySelector("#email");
  const password = document.querySelector("#password");
  const error = document.querySelector("#error");
  const submit = document.querySelector("#submit");
  let mode = "signin";

  function setMode(next) {
    mode = next;
    signinTab.classList.toggle("active", mode === "signin");
    signupTab.classList.toggle("active", mode === "signup");
    usernameWrap.classList.toggle("hidden", mode !== "signup");
    username.required = mode === "signup";
    document.querySelector("#heading").textContent = mode === "signin" ? "Good to see you." : "Make it yours.";
    document.querySelector("#subheading").textContent = mode === "signin" ? "Your private corner of the internet." : "Create your account for your private space.";
    submit.innerHTML = (mode === "signin" ? "Sign in" : "Create account") + " <span>↗</span>";
    password.autocomplete = mode === "signin" ? "current-password" : "new-password";
    error.classList.add("hidden");
  }
  signinTab.addEventListener("click", () => setMode("signin"));
  signupTab.addEventListener("click", () => setMode("signup"));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.classList.add("hidden");
    submit.disabled = true;
    submit.textContent = mode === "signin" ? "Signing in…" : "Creating account…";
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email: email.value, password: password.value, username: username.value})
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not sign in.");
      location.href = result.redirect || "/chat";
    } catch (e) {
      error.textContent = e.message || "Something went wrong.";
      error.classList.remove("hidden");
      submit.disabled = false;
      setMode(mode);
    }
  });
})();
