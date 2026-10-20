import Image from "next/image";

import type { Character } from "@/lib/characters";

/**
 * A character portrait. Falls back to the emoji with a glow, exactly as
 * show_character() did when an image was missing from data/images.
 */
export function CharacterPortrait({ character, size = 160 }: { character: Character; size?: number }) {
  if (!character.image) {
    return (
      <div
        className="text-center"
        style={{ fontSize: size / 2.5, filter: "drop-shadow(0 0 20px rgba(245,158,11,0.6))" }}
        aria-hidden
      >
        {character.emoji}
      </div>
    );
  }

  return (
    <div className="char-frame shrink-0" style={{ width: size }}>
      <Image
        src={`/characters/${character.image}`}
        alt=""
        width={size}
        height={size}
        className="h-auto w-full"
        priority={false}
      />
    </div>
  );
}

export function CharacterQuote({ character }: { character: Character }) {
  return (
    <p className="character-quote">
      &ldquo;{character.quote}&rdquo;
      {character.attribution ? ` — ${character.attribution}` : ""}
    </p>
  );
}

/** The header every tab shares: gradient title, quote, portrait on the right. */
export function TabHeader({
  title,
  character,
  children,
}: {
  title: string;
  character: Character;
  children?: React.ReactNode;
}) {
  return (
    <header className="mb-4">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <h2 className="glow-title text-[1.9rem]">{title}</h2>
          <div className="mt-2.5">
            <CharacterQuote character={character} />
          </div>
          {children ? <div className="mt-3 text-sm text-dim">{children}</div> : null}
        </div>
        <div className="hidden sm:block">
          <CharacterPortrait character={character} size={150} />
        </div>
      </div>
      <hr className="mt-5 border-line" />
    </header>
  );
}
