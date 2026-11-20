async function postAction(url, fields) {
    const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "X-CSRFToken": token,
        },
        mode: "same-origin",
        body: new URLSearchParams(fields),
    });

    if (response.status === 401) {
        const login = new URL(document.body.dataset.loginUrl, window.location.origin);
        login.searchParams.set("next", window.location.pathname + window.location.search + window.location.hash);
        window.location.assign(login);
        return null;
    }

    const data = response.headers.get("content-type")?.includes("application/json")
        ? await response.json()
        : {};
    if (!response.ok) {
        const formError = Object.values(data.errors || {}).flat()[0]?.message;
        throw new Error(data.error || formError || `Ошибка запроса (${response.status}).`);
    }
    return data;
}

document.querySelectorAll("[data-vote-url]").forEach((widget) => {
    const buttons = [...widget.querySelectorAll("[data-value]")];
    widget.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-value]");
        if (!button || button.disabled) return;

        const originalVote = buttons.find((item) => item.getAttribute("aria-pressed") === "true");
        let myVote = originalVote?.dataset.value;
        buttons.forEach((item) => { item.disabled = true; });

        try {
            const result = await postAction(widget.dataset.voteUrl, {
                target_id: widget.dataset.targetId,
                value: button.dataset.value,
            });
            if (!result) return;
            widget.querySelector(".vote-count").textContent = result.rating;
            myVote = String(result.my_vote);
        } catch (error) {
            window.alert(error.message);
        } finally {
            buttons.forEach((item) => {
                const selected = item.dataset.value === myVote;
                item.disabled = selected;
                item.setAttribute("aria-pressed", String(selected));
                item.classList.toggle("is-liked", selected && myVote === "1");
                item.classList.toggle("is-disliked", selected && myVote === "-1");
            });
        }
    });
});

const correctInputs = [...document.querySelectorAll("[data-correct-url]")];
correctInputs.forEach((input) => {
    input.addEventListener("change", async () => {
        const requested = input.checked;
        correctInputs.forEach((item) => { item.disabled = true; });

        try {
            const result = await postAction(input.dataset.correctUrl, {
                question_id: input.dataset.questionId,
                answer_id: input.dataset.answerId,
                checked: requested ? "1" : "0",
            });
            if (!result) return;

            const correctIds = new Set(result.correct_answer_ids.map(String));
            correctInputs.forEach((item) => {
                item.checked = correctIds.has(item.dataset.answerId);
                item.closest("article").classList.toggle("border-success", item.checked);
                item.labels[0].classList.toggle("text-success", item.checked);
            });
        } catch (error) {
            input.checked = !requested;
            window.alert(error.message);
        } finally {
            correctInputs.forEach((item) => { item.disabled = false; });
        }
    });
});
