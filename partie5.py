#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Partie 5 : Interface Utilisateur
# Points de contact avec l'utilisateur - Console, Web et API

import argparse
import json
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

try:
    from flask import Flask, request, jsonify, render_template_string
    _FLASK_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency for console/demo
    Flask = None  # type: ignore
    request = None  # type: ignore
    jsonify = None  # type: ignore
    render_template_string = None  # type: ignore
    _FLASK_AVAILABLE = False

# Import des parties précédentes (avec fallbacks sûrs pour démo)
try:
    from partie1 import BaseDonneesCentrale, Configuration  # type: ignore
    from partie2 import TransformateurSymbolique, ConnecteurLLM  # type: ignore
    from partie3 import (
        ModuleRaisonnementLogique,
        ModuleGestionContexte,
        ModuleGestionEmotions,
        MoteurInference,
    )  # type: ignore
    from partie4 import (
        GenerateurReponses,
        SynthetiseurConnaissance,
        FormatteurSortie,
        ProcesseurLangueNaturelle,
    )  # type: ignore
    _PARTIES_DISPONIBLES = True
except Exception:
    _PARTIES_DISPONIBLES = False

    class Configuration:
        def __init__(self) -> None:
            self._data: Dict[str, object] = {
                "version": "1.0",
                "mode_debug": False,
                "seuil_confiance_minimum": 0.3,
                "taille_max_memoire_court_terme": 100,
            }

        def charger(self, chemin: str) -> None:
            try:
                with open(chemin, "r", encoding="utf-8") as f:
                    contenu = json.load(f)
                if isinstance(contenu, dict):
                    self._data.update(contenu)
            except FileNotFoundError:
                pass

        def obtenir(self, cle: str, defaut: object = None) -> object:
            return self._data.get(cle, defaut)

        def modifier(self, cle: str, valeur: object) -> None:
            self._data[cle] = valeur

    class _InMemoryCursor:
        def __init__(self, db: "BaseDonneesCentrale") -> None:
            self._db = db
            self._last_result: Optional[List[tuple]] = None

        def execute(self, query: str, params: tuple = ()) -> "_InMemoryCursor":
            q = query.strip().lower()
            if q.startswith("select count(*) from symboles"):
                self._last_result = [(self._db.counts.get("symboles", 0),)]
            elif q.startswith("select count(*) from relations"):
                self._last_result = [(self._db.counts.get("relations", 0),)]
            elif q.startswith("select count(*) from regles_logiques"):
                self._last_result = [(self._db.counts.get("regles_logiques", 0),)]
            elif q.startswith("select count(*) from memoire_a_court_terme"):
                self._last_result = [(0,)]
            elif q.startswith("select type, count(*) from symboles group by type"):
                self._last_result = [(t, c) for t, c in self._db.symboles_par_type.items()]
            elif q.startswith("select type_relation, count(*) from relations group by type_relation"):
                self._last_result = [(t, c) for t, c in self._db.relations_par_type.items()]
            elif q.startswith("insert into feedback"):
                try:
                    session_id, requete, reponse, evaluation = params
                except Exception:
                    session_id, requete, reponse, evaluation = (None, None, None, None)
                self._db.feedback.append(
                    {
                        "session_id": session_id,
                        "requete": requete,
                        "reponse": reponse,
                        "evaluation": evaluation,
                        "timestamp": datetime.now(),
                    }
                )
                self._last_result = None
            elif q.startswith("delete from memoire_a_court_terme"):
                self._last_result = None
            else:
                # Requête inconnue, renvoyer vide par défaut
                self._last_result = []
            return self

        def fetchone(self) -> Optional[tuple]:
            if self._last_result:
                return self._last_result[0]
            return (0,)

        def fetchall(self) -> List[tuple]:
            return self._last_result or []

        def close(self) -> None:
            return None

    class _InMemoryConnection:
        def __init__(self, db: "BaseDonneesCentrale") -> None:
            self._db = db

        def cursor(self) -> _InMemoryCursor:
            return _InMemoryCursor(self._db)

        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    class BaseDonneesCentrale:
        def __init__(self) -> None:
            self.connexion = _InMemoryConnection(self)
            self.counts: Dict[str, int] = {"symboles": 0, "relations": 0, "regles_logiques": 0}
            self.symboles_par_type: Dict[str, int] = {}
            self.relations_par_type: Dict[str, int] = {}
            self.feedback: List[Dict[str, object]] = []

        def fermer(self) -> None:
            self.connexion.close()

    class TransformateurSymbolique:
        def __init__(self, db: BaseDonneesCentrale, config: Configuration) -> None:
            self.db = db
            self.config = config

    class ConnecteurLLM:
        def __init__(self, config: Configuration) -> None:
            self.config = config

    class ModuleRaisonnementLogique:
        def __init__(self, db: BaseDonneesCentrale, config: Configuration) -> None:
            self.db = db
            self.config = config

    class ModuleGestionContexte:
        def __init__(self, db: BaseDonneesCentrale, config: Configuration) -> None:
            self.db = db
            self.config = config
            self.session_actuelle: str = uuid.uuid4().hex
            self._historique: List[Dict[str, object]] = []

        def nouvelle_session(self) -> str:
            self.session_actuelle = uuid.uuid4().hex
            self._historique.append({"timestamp": datetime.now(), "type": "nouvelle_session"})
            return self.session_actuelle

        def analyser_evolution_contexte(self) -> Dict[str, object]:
            return {
                "evolution": "stable",
                "taille_historique": len(self._historique),
            }

    class ModuleGestionEmotions:
        def __init__(self, config: Configuration) -> None:
            self.config = config
            self.etat_actuel: str = "neutre"
            self.historique_emotions: List[Dict[str, object]] = []

        def set_emotion(self, nouvelle: str) -> None:
            ancienne = self.etat_actuel
            self.etat_actuel = nouvelle
            self.historique_emotions.append(
                {
                    "timestamp": datetime.now(),
                    "ancienne_emotion": ancienne,
                    "nouvelle_emotion": nouvelle,
                }
            )

    class MoteurInference:
        def __init__(self, raisonnement: ModuleRaisonnementLogique, contexte: ModuleGestionContexte, emotions: ModuleGestionEmotions) -> None:
            self.raisonnement = raisonnement
            self.contexte = contexte
            self.emotions = emotions

        def traiter_requete_complete(self, question: str) -> Dict[str, object]:
            # Heuristique triviale pour démo
            confiance = 0.75 if question else 0.0
            emotion_detectee = "neutre"
            if any(mot in question.lower() for mot in ["triste", "mal", "peur", "anxieux"]):
                emotion_detectee = "empathique"
            self.emotions.set_emotion("curieux")
            return {
                "question": question,
                "confiance": confiance,
                "emotion_detectee": emotion_detectee,
                "analyse_symbolique": {"concepts": [], "relations": []},
            }

    class GenerateurReponses:
        def __init__(self, db: BaseDonneesCentrale, config: Configuration) -> None:
            self.db = db
            self.config = config

        def generer(self, question: str, contexte: Dict[str, object]) -> str:
            return f"Réponse synthétique à: {question}"

    class SynthetiseurConnaissance:
        def __init__(self, db: BaseDonneesCentrale, generateur: GenerateurReponses) -> None:
            self.db = db
            self.generateur = generateur

        def synthetiser_reponse_hybride(self, question: str, resultat_cognitif: Dict[str, object], utiliser_llm: bool) -> Dict[str, object]:
            reponse = self.generateur.generer(question, resultat_cognitif)
            confiance = resultat_cognitif.get("confiance", 0.6)  # type: ignore[arg-type]
            methode = "hybride" if utiliser_llm else "symbolique"
            return {
                "reponse_finale": reponse,
                "confiance_finale": confiance,
                "methode_utilisee": methode,
                "metadata": {
                    "confiance": confiance,
                    "methode": methode,
                },
            }

    class FormatteurSortie:
        def __init__(self, config: Configuration) -> None:
            self.config = config

        def formater_pour_console(self, reponse_complete: Dict[str, object]) -> str:
            texte = reponse_complete.get("reponse_finale", "")
            confiance = reponse_complete.get("confiance_finale", 0)
            methode = reponse_complete.get("methode_utilisee", "symbolique")
            return f"Réponse: {texte}\nConfiance: {confiance:.2f} | Méthode: {methode}"

        def formater_pour_web(self, reponse_complete: Dict[str, object]) -> Dict[str, object]:
            return {
                "reponse": reponse_complete.get("reponse_finale", ""),
                "metadata": {
                    "confiance": reponse_complete.get("confiance_finale", 0),
                    "methode": reponse_complete.get("methode_utilisee", "symbolique"),
                },
            }

        def formater_pour_markdown(self, reponse_complete: Dict[str, object]) -> str:
            return f"### Réponse\n\n{reponse_complete.get('reponse_finale', '')}\n\n---\nConfiance: {reponse_complete.get('confiance_finale', 0):.2f}"

    class ProcesseurLangueNaturelle:
        def ameliorer_fluidite(self, texte: str) -> str:
            return texte


class InterfaceConsole:
    """
    Interface en ligne de commande pour interaction directe
    """

    def __init__(self, systeme_ia) -> None:
        self.systeme = systeme_ia
        self.historique: List[Dict[str, object]] = []
        self.commandes_speciales = {
            "/aide": self._afficher_aide,
            "/status": self._afficher_status,
            "/debug": self._toggle_debug,
            "/clear": self._effacer_historique,
            "/session": self._nouvelle_session,
            "/stats": self._afficher_statistiques,
            "/exit": self._quitter,
        }

    def demarrer(self) -> None:
        """Démarre l'interface console interactive"""
        print("🚀 Interface Console - IA Auto-Régénérante")
        print("=" * 50)
        print("Tapez /aide pour voir les commandes disponibles")
        print("Tapez /exit pour quitter")
        print("=" * 50)

        while True:
            try:
                emotion_actuelle = self.systeme.moteur_inference.emotions.etat_actuel
                prompt = f"[{emotion_actuelle}] 🤖 > "
                entree_utilisateur = input(prompt).strip()
                if not entree_utilisateur:
                    continue
                if entree_utilisateur.startswith("/"):
                    self._executer_commande(entree_utilisateur)
                    continue
                self._traiter_question(entree_utilisateur)
            except KeyboardInterrupt:
                print("\n👋 Au revoir !")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                if self.systeme.config.obtenir("mode_debug", False):
                    import traceback

                    traceback.print_exc()

    def _executer_commande(self, commande: str) -> None:
        """Exécute une commande spéciale"""
        cmd = commande.split()[0]
        if cmd in self.commandes_speciales:
            self.commandes_speciales[cmd]()
        else:
            print(f"❌ Commande inconnue: {cmd}")
            self._afficher_aide()

    def _traiter_question(self, question: str) -> None:
        """Traite une question utilisateur complète"""
        debut = time.time()
        reponse_complete = self.systeme.traiter_question_complete(question)
        duree = time.time() - debut
        self.historique.append(
            {
                "timestamp": datetime.now(),
                "question": question,
                "reponse": reponse_complete.get("reponse_finale", ""),
                "duree": duree,
                "confiance": reponse_complete.get("confiance_finale", 0),
            }
        )
        sortie_formatee = self.systeme.formatteur.formater_pour_console(reponse_complete)
        print(sortie_formatee)
        if self.systeme.config.obtenir("mode_debug", False):
            print(f"⏱️ Traité en {duree:.2f}s")

    def _afficher_aide(self) -> None:
        """Affiche l'aide des commandes"""
        aide = (
            "\n📋 Commandes disponibles:\n"
            "/aide - Affiche cette aide\n"
            "/status - État du système\n"
            "/debug - Active/désactive le mode debug\n"
            "/clear - Efface l'historique de conversation\n"
            "/session - Démarre une nouvelle session\n"
            "/stats - Statistiques du système\n"
            "/exit - Quitte le programme\n"
        )
        print(aide)

    def _afficher_status(self) -> None:
        """Affiche l'état du système"""
        status = self.systeme.obtenir_status_complet()
        print("📊 État du système:")
        for cle, valeur in status.items():
            print(f" - {cle}: {valeur}")

    def _toggle_debug(self) -> None:
        """Active/désactive le mode debug"""
        debug_actuel = bool(self.systeme.config.obtenir("mode_debug", False))
        self.systeme.config.modifier("mode_debug", not debug_actuel)
        etat = "activé" if not debug_actuel else "désactivé"
        print(f"🐛 Mode debug {etat}")

    def _effacer_historique(self) -> None:
        """Efface l'historique de conversation"""
        self.historique.clear()
        print("🧹 Historique effacé")

    def _nouvelle_session(self) -> None:
        """Démarre une nouvelle session"""
        nouvelle_id = self.systeme.moteur_inference.contexte.nouvelle_session()
        print(f"🆕 Nouvelle session: {nouvelle_id[:12]}...")

    def _afficher_statistiques(self) -> None:
        """Affiche les statistiques détaillées"""
        stats = self.systeme.obtenir_statistiques_detaillees()
        print("📈 Statistiques détaillées:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    def _quitter(self) -> None:
        """Quitte le programme"""
        print("👋 Fermeture du système...")
        self.systeme.fermer()
        sys.exit(0)


class InterfaceWeb:
    """
    Interface web Flask pour utilisation via navigateur
    """

    def __init__(self, systeme_ia, port: int = 5000) -> None:
        if not _FLASK_AVAILABLE:
            raise RuntimeError("Flask n'est pas installé. Installez-le avec: pip install flask")
        self.systeme = systeme_ia
        self.port = port
        self.app = Flask(__name__)
        self.template_html = self._charger_template_html()
        self.configurer_routes()

    def configurer_routes(self) -> None:
        """Configure les routes de l'API web"""

        @self.app.route("/")
        def interface_principale():
            return render_template_string(self.template_html)

        @self.app.route("/api/question", methods=["POST"])
        def traiter_question_api():
            try:
                data = request.get_json()
                question = (data.get("question", "") if isinstance(data, dict) else "").strip()
                if not question:
                    return jsonify({"error": "Question vide"}), 400
                reponse_complete = self.systeme.traiter_question_complete(question)
                reponse_formatee = self.systeme.formatteur.formater_pour_web(reponse_complete)
                return jsonify(reponse_formatee)
            except Exception as e:  # pragma: no cover - runtime handling
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/status", methods=["GET"])
        def obtenir_status():
            try:
                status = self.systeme.obtenir_status_complet()
                return jsonify(status)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/stats", methods=["GET"])
        def obtenir_statistiques():
            try:
                stats = self.systeme.obtenir_statistiques_detaillees()
                return jsonify(stats)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/nouvelle-session", methods=["POST"])
        def nouvelle_session():
            try:
                session_id = self.systeme.moteur_inference.contexte.nouvelle_session()
                return jsonify({"session_id": session_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _charger_template_html(self) -> str:
        """Template HTML pour l'interface web"""
        return (
            """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IA Auto-Régénérante</title>
<style>
body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
.container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
.header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
.chat-container { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 15px; margin: 20px 0; background: #fafafa; border-radius: 5px; }
.message { margin: 10px 0; padding: 10px; border-radius: 8px; }
.user-message { background: #3498db; color: white; text-align: right; }
.ai-message { background: #2ecc71; color: white; }
.input-area { display: flex; gap: 10px; }
.question-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
.send-btn { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
.send-btn:hover { background: #2980b9; }
.status-bar { margin-top: 20px; padding: 10px; background: #ecf0f1; border-radius: 5px; font-size: 12px; }
.loading { display: none; text-align: center; color: #7f8c8d; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🤖 IA Auto-Régénérante</h1>
<p>Système d'Intelligence Artificielle avec Raisonnement Symbolique</p>
</div>
<div id="chat" class="chat-container">
<div class="ai-message">
👋 Bonjour ! Je suis votre IA auto-régénérante. Posez-moi une question !
</div>
</div>
<div class="input-area">
<input type="text" id="questionInput" class="question-input" placeholder="Posez votre question..." onkeypress="if(event.key==='Enter') envoyerQuestion()">
<button class="send-btn" onclick="envoyerQuestion()">Envoyer</button>
</div>
<div class="loading" id="loading">⏳ L'IA réfléchit...</div>
<div class="status-bar" id="status">
État: Prêt | Session: Nouvelle | Émotion: Neutre
</div>
</div>
<script>
async function envoyerQuestion() {
const input = document.getElementById('questionInput');
const question = input.value.trim();
if (!question) return;
ajouterMessage(question, 'user-message');
input.value = '';
document.getElementById('loading').style.display = 'block';
try {
const response = await fetch('/api/question', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ question: question })
});
const data = await response.json();
if (data.error) {
ajouterMessage('❌ ' + data.error, 'ai-message');
} else {
ajouterMessage(data.reponse, 'ai-message');
mettreAJourStatus(data.metadata);
}
} catch (error) {
ajouterMessage('❌ Erreur de connexion: ' + error.message, 'ai-message');
}
document.getElementById('loading').style.display = 'none';
}
function ajouterMessage(message, classe) {
const chat = document.getElementById('chat');
const div = document.createElement('div');
div.className = 'message ' + classe;
div.textContent = message;
chat.appendChild(div);
chat.scrollTop = chat.scrollHeight;
}
function mettreAJourStatus(metadata) {
if (metadata) {
const status = document.getElementById('status');
status.textContent = `État: Actif | Confiance: ${(metadata.confiance * 100).toFixed(0)}% | Méthode: ${metadata.methode}`;
}
}
document.addEventListener('DOMContentLoaded', () => {
document.getElementById('questionInput').focus();
});
</script>
</body>
</html>
"""
        )

    def demarrer(self) -> None:
        """Démarre le serveur web"""
        print(f"🌐 Démarrage du serveur web sur http://localhost:{self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False)


class InterfaceAPI:
    """
    Interface API REST pour intégration avec d'autres applications
    """

    def __init__(self, systeme_ia, port: int = 5001) -> None:
        if not _FLASK_AVAILABLE:
            raise RuntimeError("Flask n'est pas installé. Installez-le avec: pip install flask")
        self.systeme = systeme_ia
        self.port = port
        self.app = Flask(__name__)
        self.cles_api_valides = set()  # Pour authentification future
        self.configurer_api()

    def configurer_api(self) -> None:
        """Configure les endpoints de l'API"""

        @self.app.after_request
        def after_request(response):  # type: ignore[override]
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE")
            return response

        @self.app.route("/api/v1/question", methods=["POST"])
        def api_question():
            """Endpoint principal pour poser une question"""
            try:
                data = request.get_json()
                question = (data.get("question", "") if isinstance(data, dict) else "").strip()
                options = (data.get("options", {}) if isinstance(data, dict) else {})
                if not question:
                    return (
                        jsonify({"success": False, "error": "Question requise", "code": "QUESTION_MANQUANTE"}),
                        400,
                    )
                utiliser_llm = bool(options.get("utiliser_llm", True))
                format_sortie = str(options.get("format", "standard"))
                reponse = self.systeme.traiter_question_complete(question, utiliser_llm)
                if format_sortie == "markdown":
                    reponse_formatee = self.systeme.formatteur.formater_pour_markdown(reponse)
                    return jsonify(
                        {
                            "success": True,
                            "reponse": reponse_formatee,
                            "format": "markdown",
                            "metadata": reponse.get("metadata", {}),
                        }
                    )
                return jsonify(
                    {
                        "success": True,
                        "reponse": reponse.get("reponse_finale", ""),
                        "metadata": {
                            "confiance": reponse.get("confiance_finale", 0),
                            "methode": reponse.get("methode_utilisee", "symbolique"),
                            "duree_traitement": reponse.get("duree_traitement", 0),
                            "emotion_detectee": reponse.get("emotion_detectee", "neutre"),
                        },
                    }
                )
            except Exception as e:
                return jsonify({"success": False, "error": str(e), "code": "ERREUR_TRAITEMENT"}), 500

        @self.app.route("/api/v1/status", methods=["GET"])
        def api_status():
            """État complet du système"""
            try:
                status = self.systeme.obtenir_status_complet()
                return jsonify({"success": True, "status": status, "timestamp": datetime.now().isoformat()})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/v1/session/nouvelle", methods=["POST"])
        def api_nouvelle_session():
            """Crée une nouvelle session"""
            try:
                session_id = self.systeme.moteur_inference.contexte.nouvelle_session()
                return jsonify({"success": True, "session_id": session_id})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/v1/apprentissage/feedback", methods=["POST"])
        def api_feedback():
            """Enregistre un feedback pour l'apprentissage"""
            try:
                data = request.get_json()
                question = (data.get("question", "") if isinstance(data, dict) else "").strip()
                reponse = (data.get("reponse", "") if isinstance(data, dict) else "").strip()
                evaluation = int((data.get("evaluation", 0) if isinstance(data, dict) else 0))
                cursor = self.systeme.db.connexion.cursor()
                cursor.execute(
                    """
INSERT INTO feedback (session_id, requete, reponse, evaluation)
VALUES (?, ?, ?, ?)
""",
                    (
                        self.systeme.moteur_inference.contexte.session_actuelle,
                        question,
                        reponse,
                        evaluation,
                    ),
                )
                self.systeme.db.connexion.commit()
                return jsonify({"success": True, "message": "Feedback enregistré"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/v1/documentation", methods=["GET"])
        def api_documentation():
            """Documentation de l'API"""
            doc = {
                "nom": "API IA Auto-Régénérante",
                "version": "1.0",
                "endpoints": {
                    "POST /api/v1/question": {
                        "description": "Pose une question au système IA",
                        "parametres": {
                            "question": "string (requis)",
                            "options": {
                                "utiliser_llm": "boolean (optionnel, défaut: true)",
                                "format": "string (optionnel: 'standard' ou 'markdown')",
                            },
                        },
                    },
                    "GET /api/v1/status": "État du système",
                    "POST /api/v1/session/nouvelle": "Crée une nouvelle session",
                    "POST /api/v1/apprentissage/feedback": "Enregistre un feedback",
                },
            }
            return jsonify(doc)

    def demarrer(self) -> None:
        """Démarre le serveur API"""
        print(f"🔌 API REST démarrée sur http://localhost:{self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False)


class SystemeIAComplet:
    """
    Orchestrateur principal qui combine tous les modules
    """

    def __init__(self, config_file: str = "config.json") -> None:
        print("🏗️ Initialisation du Système IA Complet...")
        self.config = Configuration()
        if config_file:
            self.config.charger(config_file)
        self.db = BaseDonneesCentrale()
        self.transformateur = TransformateurSymbolique(self.db, self.config)
        self.raisonnement = ModuleRaisonnementLogique(self.db, self.config)
        self.contexte = ModuleGestionContexte(self.db, self.config)
        self.emotions = ModuleGestionEmotions(self.config)
        self.moteur_inference = MoteurInference(self.raisonnement, self.contexte, self.emotions)
        self.generateur = GenerateurReponses(self.db, self.config)
        self.synthetiseur = SynthetiseurConnaissance(self.db, self.generateur)
        self.formatteur = FormatteurSortie(self.config)
        self.processeur_nl = ProcesseurLangueNaturelle()
        print("✅ Système IA initialisé avec succès")

    def traiter_question_complete(self, question: str, utiliser_llm: bool = True) -> Dict[str, object]:
        """
        Traite une question de bout en bout - méthode principale du système
        """
        debut = time.time()
        resultat_cognitif = self.moteur_inference.traiter_requete_complete(question)
        reponse_data = self.synthetiseur.synthetiser_reponse_hybride(question, resultat_cognitif, utiliser_llm)
        reponse_data["reponse_finale"] = self.processeur_nl.ameliorer_fluidite(str(reponse_data.get("reponse_finale", "")))
        duree = time.time() - debut
        reponse_data["duree_traitement"] = duree
        reponse_data["timestamp"] = datetime.now().isoformat()
        reponse_data["emotion_detectee"] = resultat_cognitif.get("emotion_detectee", "neutre")
        return reponse_data

    def obtenir_status_complet(self) -> Dict[str, object]:
        """Obtient l'état complet du système"""
        cursor = self.db.connexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM symboles")
        nb_symboles = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM relations")
        nb_relations = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM regles_logiques")
        nb_regles = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM memoire_a_court_terme WHERE session_id = ?",
            (self.contexte.session_actuelle,),
        )
        nb_memoire = cursor.fetchone()[0]
        return {
            "version": self.config.obtenir("version", "1.0"),
            "etat": "actif",
            "session_actuelle": str(self.contexte.session_actuelle)[:12] + "...",
            "emotion_actuelle": getattr(self.emotions, "etat_actuel", "neutre"),
            "base_donnees": {
                "symboles": nb_symboles,
                "relations": nb_relations,
                "regles": nb_regles,
                "memoire_active": nb_memoire,
            },
            "configuration": {
                "mode_debug": self.config.obtenir("mode_debug", False),
                "seuil_confiance": self.config.obtenir("seuil_confiance_minimum", 0.3),
            },
        }

    def obtenir_statistiques_detaillees(self) -> Dict[str, object]:
        """Obtient des statistiques détaillées du système"""
        cursor = self.db.connexion.cursor()
        cursor.execute("SELECT type, COUNT(*) FROM symboles GROUP BY type")
        symboles_par_type = dict(cursor.fetchall())
        cursor.execute("SELECT type_relation, COUNT(*) FROM relations GROUP BY type_relation")
        relations_par_type = dict(cursor.fetchall())
        evolution_contexte = self.contexte.analyser_evolution_contexte()
        historique_emotions = self.emotions.historique_emotions[-10:]
        return {
            "timestamp": datetime.now().isoformat(),
            "symboles_par_type": symboles_par_type,
            "relations_par_type": relations_par_type,
            "contexte": evolution_contexte,
            "historique_emotions": [
                {
                    "timestamp": em.get("timestamp").isoformat() if hasattr(em.get("timestamp"), "isoformat") else str(em.get("timestamp")),
                    "transition": f"{em.get('ancienne_emotion', '')} → {em.get('nouvelle_emotion', '')}",
                }
                for em in historique_emotions
            ],
            "performance": {
                "seuil_confiance": self.config.obtenir("seuil_confiance_minimum", 0.3),
                "taille_memoire": self.config.obtenir("taille_max_memoire_court_terme", 100),
            },
        }

    def fermer(self) -> None:
        """Ferme proprement le système"""
        print("🔒 Fermeture du système...")
        if hasattr(self, "db") and self.db:
            self.db.fermer()
        print("✅ Système fermé")


def demarrer_interface_console(systeme: SystemeIAComplet) -> None:
    interface = InterfaceConsole(systeme)
    interface.demarrer()


def demarrer_interface_web(systeme: SystemeIAComplet, port: int = 5000) -> None:
    interface = InterfaceWeb(systeme, port)
    interface.demarrer()


def demarrer_api(systeme: SystemeIAComplet, port: int = 5001) -> None:
    interface = InterfaceAPI(systeme, port)
    interface.demarrer()


def demonstration_complete(systeme: SystemeIAComplet) -> None:
    """Démonstration complète de toutes les interfaces"""
    print("🚀 Démonstration Partie 5 - Interfaces Utilisateur")
    questions_demo = [
        "Qu'est-ce qu'un chat ?",
        "Comment fonctionne la photosynthèse ?",
        "Pourquoi la lune brille-t-elle ?",
    ]
    print("\n💻 Test Interface Console (simulation):")
    for i, question in enumerate(questions_demo):
        print(f"\n[Test {i+1}] Question: {question}")
        reponse = systeme.traiter_question_complete(question)
        sortie_console = systeme.formatteur.formater_pour_console(reponse)
        print(sortie_console[:300] + "..." if len(sortie_console) > 300 else sortie_console)
    print("\n🌐 Interface Web disponible sur: http://localhost:5000")
    print("🔌 API REST disponible sur: http://localhost:5001")
    print("\n📚 Endpoints API disponibles:")
    endpoints = [
        "POST /api/v1/question - Poser une question",
        "GET /api/v1/status - État du système",
        "POST /api/v1/session/nouvelle - Nouvelle session",
        "POST /api/v1/apprentissage/feedback - Envoyer feedback",
        "GET /api/v1/documentation - Documentation API",
    ]
    for endpoint in endpoints:
        print(f" - {endpoint}")
    print("\n📊 Statistiques du système:")
    stats = systeme.obtenir_statistiques_detaillees()
    print(f" - Symboles par type: {stats.get('symboles_par_type')}")
    print(f" - Relations par type: {stats.get('relations_par_type')}")
    contexte = stats.get("contexte", {})
    evo = contexte.get("evolution", "inconnue") if isinstance(contexte, dict) else "inconnue"
    print(f" - Évolution contexte: {evo}")
    print(f" - Émotion actuelle: {systeme.emotions.etat_actuel}")
    print("\n🎯 Instructions d'utilisation:")
    print(" 1. Console: python partie5.py --interface console")
    print(" 2. Web: python partie5.py --interface web --port 5000")
    print(" 3. API: python partie5.py --interface api --port 5001")
    print("\n✅ Partie 5 terminée avec succès!")
    print("📝 Prêt pour la Partie 6 : Boucle d'Apprentissage et Intégration Finale")


# Gestionnaire de sessions multiples
class GestionnaireSessionsMultiples:
    """
    Gère plusieurs sessions utilisateur simultanées
    """

    def __init__(self, systeme: SystemeIAComplet) -> None:
        self.systeme = systeme
        self.sessions_actives: Dict[str, Dict[str, object]] = {}
        self.verrou_sessions = threading.Lock()

    def creer_session(self, user_id: Optional[str] = None) -> str:
        """Crée une nouvelle session utilisateur"""
        with self.verrou_sessions:
            session_id = self.systeme.contexte.nouvelle_session()
            self.sessions_actives[session_id] = {
                "user_id": user_id,
                "creation": datetime.now(),
                "derniere_activite": datetime.now(),
                "nb_interactions": 0,
                "contexte_prive": {},
            }
            return session_id

    def traiter_question_session(self, session_id: str, question: str) -> Dict[str, object]:
        """Traite une question dans le contexte d'une session spécifique"""
        with self.verrou_sessions:
            if session_id not in self.sessions_actives:
                raise ValueError(f"Session {session_id} introuvable")
            self.sessions_actives[session_id]["derniere_activite"] = datetime.now()
            self.sessions_actives[session_id]["nb_interactions"] = int(
                self.sessions_actives[session_id].get("nb_interactions", 0)
            ) + 1
            self.systeme.contexte.session_actuelle = session_id
        return self.systeme.traiter_question_complete(question)

    def nettoyer_sessions_expirees(self, duree_expiration_heures: int = 24) -> None:
        """Nettoie les sessions expirées"""
        maintenant = datetime.now()
        sessions_a_supprimer: List[str] = []
        with self.verrou_sessions:
            for session_id, info in list(self.sessions_actives.items()):
                derniere = info.get("derniere_activite")
                if isinstance(derniere, datetime):
                    delta = (maintenant - derniere).total_seconds()
                    if delta > duree_expiration_heures * 3600:
                        sessions_a_supprimer.append(session_id)
            for session_id in sessions_a_supprimer:
                del self.sessions_actives[session_id]
                cursor = self.systeme.db.connexion.cursor()
                cursor.execute("DELETE FROM memoire_a_court_terme WHERE session_id = ?", (session_id,))
                self.systeme.db.connexion.commit()
        if sessions_a_supprimer:
            print(f"🧹 {len(sessions_a_supprimer)} sessions expirées nettoyées")


class MoniteurPerformances:
    """
    Moniteur pour surveiller les performances du système
    """

    def __init__(self, systeme: SystemeIAComplet) -> None:
        self.systeme = systeme
        self.metriques: Dict[str, float] = {
            "requetes_traitees": 0.0,
            "temps_reponse_moyen": 0.0,
            "erreurs": 0.0,
            "confiance_moyenne": 0.0,
            "utilisation_llm": 0.0,
        }
        self.historique_performances: List[Dict[str, object]] = []

    def enregistrer_performance(self, duree: float, confiance: float, utilise_llm: bool, erreur: bool = False) -> None:
        """Enregistre une métrique de performance"""
        self.metriques["requetes_traitees"] += 1.0
        if erreur:
            self.metriques["erreurs"] += 1.0
        else:
            n = int(self.metriques["requetes_traitees"] - self.metriques["erreurs"])
            if n > 0:
                self.metriques["temps_reponse_moyen"] = (
                    (self.metriques["temps_reponse_moyen"] * (n - 1) + float(duree)) / n
                )
                self.metriques["confiance_moyenne"] = (
                    (self.metriques["confiance_moyenne"] * (n - 1) + float(confiance)) / n
                )
        if utilise_llm:
            self.metriques["utilisation_llm"] += 1.0
        self.historique_performances.append(
            {
                "timestamp": datetime.now(),
                "duree": float(duree),
                "confiance": float(confiance),
                "utilise_llm": bool(utilise_llm),
                "erreur": bool(erreur),
            }
        )
        if len(self.historique_performances) > 1000:
            self.historique_performances = self.historique_performances[-1000:]

    def obtenir_rapport_performance(self) -> Dict[str, object]:
        """Génère un rapport de performance"""
        total_requetes = int(self.metriques["requetes_traitees"])
        if total_requetes == 0:
            return {"message": "Aucune donnée de performance disponible"}
        taux_erreur = (self.metriques["erreurs"] / total_requetes) * 100.0
        taux_utilisation_llm = (self.metriques["utilisation_llm"] / total_requetes) * 100.0
        return {
            "requetes_totales": total_requetes,
            "temps_reponse_moyen": round(self.metriques["temps_reponse_moyen"], 3),
            "confiance_moyenne": round(self.metriques["confiance_moyenne"], 3),
            "taux_erreur": round(taux_erreur, 2),
            "taux_utilisation_llm": round(taux_utilisation_llm, 2),
            "performance_globale": self._calculer_score_performance(),
        }

    def _calculer_score_performance(self) -> str:
        """Calcule un score de performance global"""
        if int(self.metriques["requetes_traitees"]) == 0:
            return "non_evaluee"
        temps_bon = self.metriques["temps_reponse_moyen"] < 2.0
        confiance_bonne = self.metriques["confiance_moyenne"] > 0.6
        taux_erreur_ok = (self.metriques["erreurs"] / self.metriques["requetes_traitees"]) < 0.1
        if temps_bon and confiance_bonne and taux_erreur_ok:
            return "excellente"
        if (temps_bon and confiance_bonne) or (temps_bon and taux_erreur_ok):
            return "bonne"
        if temps_bon or confiance_bonne:
            return "moyenne"
        return "faible"


class TesteurInterfaces:
    """
    Testeur automatique pour valider les interfaces
    """

    def __init__(self, systeme: SystemeIAComplet) -> None:
        self.systeme = systeme
        self.moniteur = MoniteurPerformances(systeme)

    def tester_toutes_interfaces(self) -> None:
        """Test automatique de toutes les interfaces"""
        print("🧪 Tests automatiques des interfaces")
        questions_test = [
            "Test basique: qu'est-ce qu'un ordinateur ?",
            "Test analytique: comparer chat et chien",
            "Test empathique: comment aider quelqu'un de triste ?",
            "Test curieux: pourquoi le ciel est-il bleu ?",
        ]
        for i, question in enumerate(questions_test):
            print(f"\n🔬 Test {i+1}: {question[:30]}...")
            debut = time.time()
            try:
                reponse = self.systeme.traiter_question_complete(question)
                duree = time.time() - debut
                self.moniteur.enregistrer_performance(
                    duree,
                    float(reponse.get("confiance_finale", 0)),
                    bool(reponse.get("methode_utilisee") == "hybride"),
                )
                print(f" ✅ Succès en {duree:.2f}s - Confiance: {float(reponse.get('confiance_finale', 0)):.2f}")
            except Exception as e:
                duree = time.time() - debut
                self.moniteur.enregistrer_performance(duree, 0.0, False, True)
                print(f" ❌ Erreur: {e}")
        rapport = self.moniteur.obtenir_rapport_performance()
        print("\n📈 Rapport de performance:")
        if "message" in rapport:
            print(f" - {rapport['message']}")
            return
        print(f" - Performance globale: {rapport['performance_globale']}")
        print(f" - Temps moyen: {rapport['temps_reponse_moyen']}s")
        print(f" - Confiance moyenne: {rapport['confiance_moyenne']}")
        print(f" - Taux d'erreur: {rapport['taux_erreur']}%")


def main() -> None:
    """Fonction principale avec choix d'interface"""
    parser = argparse.ArgumentParser(description="Système IA Auto-Régénérante")
    parser.add_argument(
        "--interface",
        choices=["console", "web", "api", "demo"],
        default="demo",
        help="Type d'interface à lancer",
    )
    parser.add_argument("--port", type=int, default=5000, help="Port pour web/api")
    parser.add_argument("--config", default="config.json", help="Fichier de configuration")
    args = parser.parse_args()
    systeme = SystemeIAComplet(args.config)
    try:
        if args.interface == "console":
            demarrer_interface_console(systeme)
        elif args.interface == "web":
            demarrer_interface_web(systeme, args.port)
        elif args.interface == "api":
            demarrer_api(systeme, args.port)
        else:
            demonstration_complete(systeme)
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur")
    finally:
        systeme.fermer()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.extend(["--interface", "demo"])  # mode démo par défaut si aucun argument
    main()

"""
🔧 INSTALLATION:

pip install flask spacy requests transformers

📱 UTILISATION:

1. Mode Console Interactive:
   python partie5.py --interface console

2. Interface Web:
   python partie5.py --interface web --port 5000
   Puis ouvrir: http://localhost:5000

3. API REST:
   python partie5.py --interface api --port 5001

4. Démonstration:
   python partie5.py --interface demo

🔗 INTÉGRATION:
- Console: Interaction directe en ligne de commande
- Web: Interface graphique dans le navigateur
- API: Intégration avec autres applications via REST
- Multi-sessions: Support de plusieurs utilisateurs simultanés
"""