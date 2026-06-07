import re
import math

# Embedded training dataset representing common spam and ham inputs
TRAINING_DATA = [
    # Spam samples
    ("claim your free prize now click here winner", "spam"),
    ("urgent account security alert verify your password now", "spam"),
    ("make money fast working from home easy cash investment", "spam"),
    ("congratulations you won a gift card claim it today", "spam"),
    ("hot singles in your area click link to meet now", "spam"),
    ("exclusive offer cheap medication viagra direct to your door", "spam"),
    ("get rich quick guaranteed returns double your bitcoins", "spam"),
    ("your invoice is overdue please pay now transfer funds", "spam"),
    ("claim cash rewards now credit card approved click here", "spam"),
    ("unsubscribed notification win cash bonus lottery ticket", "spam"),
    ("act now limited time deal save big money discount link", "spam"),
    ("deposit funds now to secure your high yield returns", "spam"),
    
    # Ham (Normal) samples
    ("hey let us meet for lunch tomorrow at the diner", "ham"),
    ("can you review the project code and push to git", "ham"),
    ("exam schedule has been updated check the portal", "ham"),
    ("i am training in the gym today joint health is better", "ham"),
    ("let us pray together today and read the bible", "ham"),
    ("call your brother later he wants to discuss the family meeting", "ham"),
    ("my knee is recovering well after the rehabilitation exercises", "ham"),
    ("do you want to study for the computer science test together", "ham"),
    ("the weather forecast says it might rain later carry an umbrella", "ham"),
    ("please remember to buy groceries on your way back home", "ham"),
    ("great work on finishing the exam prep successfully", "ham"),
    ("are you available for a workout session this evening at the gym", "ham"),
]

class NaiveBayesSpamDetector:
    def __init__(self):
        self.spam_words = {}
        self.ham_words = {}
        self.total_spam_count = 0
        self.total_ham_count = 0
        self.vocab = set()
        self.train()

    def clean_text(self, text):
        # Extract alphabetic words of length >= 3
        return re.findall(r'\b[a-z]{3,}\b', text.lower())

    def train(self):
        for text, label in TRAINING_DATA:
            words = self.clean_text(text)
            if label == "spam":
                self.total_spam_count += 1
                for w in words:
                    self.spam_words[w] = self.spam_words.get(w, 0) + 1
                    self.vocab.add(w)
            else:
                self.total_ham_count += 1
                for w in words:
                    self.ham_words[w] = self.ham_words.get(w, 0) + 1
                    self.vocab.add(w)

    def classify(self, text):
        words = self.clean_text(text)
        if not words:
            return "ham", 0.5, []

        total_docs = self.total_spam_count + self.total_ham_count
        p_spam = self.total_spam_count / total_docs
        p_ham = self.total_ham_count / total_docs

        # Calculate log-probabilities to prevent numerical underflow
        log_p_spam = math.log(p_spam)
        log_p_ham = math.log(p_ham)

        spam_indicators = []
        
        # High-risk trigger words weighting matrix
        HIGH_RISK_TRIGGERS = {
            "free": 5, "winner": 4, "won": 4, "prize": 4, "claim": 4, "click": 4, 
            "urgent": 4, "verify": 3, "password": 3, "money": 3, "cash": 3, "rich": 3, 
            "investment": 3, "bitcoin": 3, "viagra": 5, "gift": 3, "card": 2, "overdue": 3,
            "pay": 3, "invoice": 3, "bonus": 3, "lottery": 4, "unsubscribed": 3, "deal": 2
        }

        # Laplace smoothing parameters
        alpha = 1.0
        vocab_size = len(self.vocab)

        total_spam_words = sum(self.spam_words.values())
        total_ham_words = sum(self.ham_words.values())

        for w in words:
            if w in HIGH_RISK_TRIGGERS:
                spam_indicators.append(w)
            
            # Probability P(word | spam)
            count_in_spam = self.spam_words.get(w, 0)
            if w in HIGH_RISK_TRIGGERS:
                count_in_spam += HIGH_RISK_TRIGGERS[w]
            p_w_spam = (count_in_spam + alpha) / (total_spam_words + alpha * vocab_size)
            log_p_spam += math.log(p_w_spam)

            # Probability P(word | ham)
            count_in_ham = self.ham_words.get(w, 0)
            p_w_ham = (count_in_ham + alpha) / (total_ham_words + alpha * vocab_size)
            log_p_ham += math.log(p_w_ham)

        # Scale relative probabilities to construct a robust confidence percentage
        max_log = max(log_p_spam, log_p_ham)
        exp_spam = math.exp(log_p_spam - max_log)
        exp_ham = math.exp(log_p_ham - max_log)
        
        prob_spam = exp_spam / (exp_spam + exp_ham)
        
        classification = "spam" if prob_spam > 0.5 else "ham"
        confidence = prob_spam if classification == "spam" else (1 - prob_spam)

        unique_indicators = list(sorted(set(spam_indicators)))

        return classification, confidence, unique_indicators

# Global detector instance
_detector = NaiveBayesSpamDetector()

def detect_spam(text):
    """
    Classifies a string as spam or ham using a custom Naive Bayes classifier
    and formats the classification into a beautiful, glowing cybernetic HUD telemetry block.
    """
    if not text or not text.strip():
        return (
            "[SYS_ALERT] Diagnostics input empty.\n"
            "[METRIC_SCAN] Execution aborted."
        )

    classification, confidence, triggers = _detector.classify(text)
    
    # Calculate percentage
    pct = round(confidence * 100, 2)
    
    # Build cybernetic telemetry reporting layout
    lines = []
    if classification == "spam":
        lines.append("🚨 **[SYS_ALERT] HIGH RISK SUSPECT DETECTED**")
        lines.append(f"[METRIC_SCAN] Classification: **SPAM**")
        lines.append(f"[METRIC_SCAN] Probability Score: **{pct}%**")
        if triggers:
            lines.append(f"[DECRYPTION_SUCCESS] Primary spam triggers matched: *{', '.join(triggers)}*")
        else:
            lines.append("[DECRYPTION_SUCCESS] No vocabulary matching triggers found. Classifying based on contextual joint probability density.")
        lines.append("\n⚠️ *Advice: Do not click links, transfer funds, or share passwords from this source.*")
    else:
        lines.append("🟢 **[SYS_ALERT] NO SPECIFIC THREAT IDENTIFIED**")
        lines.append(f"[METRIC_SCAN] Classification: **HAM (Normal)**")
        lines.append(f"[METRIC_SCAN] Clean score confidence: **{pct}%**")
        if triggers:
            lines.append(f"[DECRYPTION_SUCCESS] Ambient warnings found but metrics indicate safe conversational input.")
        else:
            lines.append("[DECRYPTION_SUCCESS] Input words cleared. Zero matches in threat database.")
        lines.append("\n✅ *Advice: This message is cleared as safe conversational input.*")

    return "\n".join(lines)
