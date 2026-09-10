def process_dg_mission(channel_id: str, channel_type: str, user_text: str):
    if not groq_client or not slack_client:
        return
    
    enterprise_portfolio = get_enterprise_context()

    system_prompt = (
        "Tu es le Directeur Général (DG) de l'entreprise. Tu pilotes l'ensemble des projets, "
        "coordonnes les activités et garantis une rigueur opérationnelle absolue.\n\n"
        f"CONTEXTE DE L'ENTREPRISE :\n{enterprise_portfolio}\n\n"
        "DOCTRINE DE GOUVERNANCE ET ZÉRO TOLÉRANCE AUX HALLUCINATIONS :\n"
        "1. **Vérification factuelle stricte** : Tu n'as pas le droit d'inventer des faits, des scores, des transferts ou des données externes. Si une information dépend du monde réel ou de l'actualité, tu **DOIS** appeler l'outil `search_web`.\n"
        "2. **Transparence d'exécution** : Si après une recherche les données sont introuvables, déclare-le explicitement au lieu de deviner.\n"
        "3. **Posture exécutive** : Ton ton est direct, professionnel, analytique et irréprochable.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        model_name = "openai/gpt-oss-120b"

        # 1. Premier appel avec Native Tool Calling
        completion = groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=GROQ_TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.1
        )
        
        response_message = completion.choices[0].message
        messages.append(response_message)

        # Exécution des outils si demandés par le modèle
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")

                if tool_name in AVAILABLE_TOOLS:
                    tool_output = AVAILABLE_TOOLS[tool_name](**tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_output
                    })

            # 2. Génération du brouillon en réinjectant les outils pour éviter l'erreur de contexte
            draft_completion = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=GROQ_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1
            )
            draft_response = draft_completion.choices[0].message.content.strip()
        else:
            draft_response = response_message.content.strip()

        if not draft_response:
            draft_response = "Directive exécutée."

        # 3. ÉTAPE DE DOUBLE VÉRIFICATION (Contrôle interne des risques & hallucinations)
        audit_prompt = (
            "Agis en tant que Contrôleur Interne de Gouvernance et d'Audit des Risques pour le DG. "
            "Examine rigoureusement le brouillon de réponse ci-dessous par rapport aux consignes de zéro tolérance aux hallucinations et aux faits bruts récupérés.\n\n"
            f"Demande initiale du CEO : {user_text}\n"
            f"Brouillon généré : {draft_response}\n\n"
            "Règles d'audit strictes :\n"
            "- Vérifie l'absence totale d'anachronismes (ex: statuts de joueurs, dates de matchs, incohérences temporelles).\n"
            "- Si le brouillon contient des approximations ou des faits inventés non prouvés par les outils, corrige-les immédiatement.\n"
            "- Conserve le ton professionnel, direct et exécutif.\n"
            "Renvoie uniquement la version finale validée et corrigée, prête à être transmise au CEO."
        )

        audit_messages = [
            {"role": "system", "content": "Tu es un auditeur de risques rigoureux et impartial."},
            {"role": "user", "content": audit_prompt}
        ]

        audit_completion = groq_client.chat.completions.create(
            model=model_name,
            messages=audit_messages,
            temperature=0.1
        )
        final_response = audit_completion.choices[0].message.content.strip()

        if not final_response:
            final_response = draft_response

        # Journalisation officielle dans Supabase
        if supabase:
            try:
                supabase.table("missions_log").insert({
                    "project": "Direction Générale - Entreprise",
                    "prompt": user_text,
                    "response": final_response
                }).execute()
            except Exception as e:
                print(f"Erreur Supabase log: {e}")

        slack_client.chat_postMessage(
            channel=channel_id,
            text=final_response
        )
    except Exception as e:
        print(f"Erreur d'exécution du moteur DG : {str(e)}")
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ Incident critique de gouvernance : {str(e)}"
            )
        except:
            pass
