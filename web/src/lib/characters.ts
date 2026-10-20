/**
 * The character assigned to each tab, carried over from dashboard.py.
 *
 * Each tab's character was chosen for what the tab does — Levi's precision for
 * search preferences, Yoriichi's focus for the board, Spike's detachment for
 * alerts. Keep the pairings; they're the personality of the thing.
 */
export interface Character {
  /** File in /public/characters, or null to use the emoji alone. */
  image: string | null;
  /** Shown when the image is missing, as show_character() did. */
  emoji: string;
  quote: string;
  attribution: string;
}

export const SIDEBAR_CHARACTER: Character = {
  image: "goku.png",
  emoji: "⚡",
  quote: "Power comes in response to a need, not a desire.",
  attribution: "Goku",
};

export const TAB_CHARACTERS: Record<string, Character> = {
  preferences: {
    image: "levi.png",
    emoji: "⚔️",
    quote: "The only time a soldier should doubt their decision is before they make it.",
    attribution: "Levi Ackerman",
  },
  board: {
    image: "yoriichi.png",
    emoji: "🌅",
    quote: "I have no fear of death. It means I can fight without holding back.",
    attribution: "Yoriichi Tsugikuni",
  },
  alerts: {
    image: "spike.png",
    emoji: "🚀",
    quote: "Whatever happens, happens.",
    attribution: "Spike Spiegel, Cowboy Bebop",
  },
  run: {
    image: "goku.png",
    emoji: "⚡",
    quote:
      "I am the hope of the universe. I am the answer to all living things that cry out for peace.",
    attribution: "Goku",
  },
  linkedin: {
    image: "itachi.png",
    emoji: "🔴",
    quote: "People live their lives bound by what they accept as correct and true.",
    attribution: "Itachi Uchiha",
  },
  connections: {
    image: "itachi.png",
    emoji: "🤝",
    quote: "The strength of a team lies in the network behind it.",
    attribution: "",
  },
};

export interface TabDef {
  key: string;
  href: string;
  icon: string;
  label: string;
}

/** Order matches dashboard.py's st.tabs() call. */
export const TABS: readonly TabDef[] = [
  { key: "preferences", href: "/preferences", icon: "⚙️", label: "Preferences" },
  { key: "board", href: "/", icon: "📋", label: "Job Board" },
  { key: "alerts", href: "/alerts", icon: "📧", label: "Alerts & Email" },
  { key: "run", href: "/run", icon: "▶️", label: "Run Agent" },
  { key: "linkedin", href: "/linkedin", icon: "🔗", label: "LinkedIn Setup" },
  { key: "connections", href: "/connections", icon: "👥", label: "Connections & Referrals" },
] as const;
