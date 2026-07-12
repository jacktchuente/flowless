export type CategoryKey =
  | "fiction"
  | "documentary"
  | "news"
  | "comedy"
  | "music"
  | "sport"
  | "filler";
export const CATEGORY_COLOR: Record<
  CategoryKey,
  { fg: string; bg: string; sw: string; label: string }
> = {
  fiction: {
    fg: "#3947a0",
    bg: "#e4e6f8",
    sw: "var(--cat-fiction)",
    label: "Fiction",
  },
  documentary: {
    fg: "#1e7167",
    bg: "#dff3ef",
    sw: "var(--cat-documentary)",
    label: "Documentaire",
  },
  news: {
    fg: "#8c3f29",
    bg: "#f8e4dc",
    sw: "var(--cat-news)",
    label: "Information",
  },
  comedy: {
    fg: "#8c6a1f",
    bg: "#f8efd9",
    sw: "var(--cat-comedy)",
    label: "Divertissement",
  },
  music: {
    fg: "#733f8a",
    bg: "#f1e3f7",
    sw: "var(--cat-music)",
    label: "Musique",
  },
  sport: {
    fg: "#873e37",
    bg: "#f5e4e2",
    sw: "var(--cat-sport)",
    label: "Sport",
  },
  filler: {
    fg: "#5c6663",
    bg: "#e7eae9",
    sw: "var(--cat-filler)",
    label: "Filler",
  },
};
export function natureToCategory(nature: unknown): CategoryKey {
  const key = String(nature ?? "").toUpperCase();
  return (
    (
      {
        FICTION: "fiction",
        DOCUMENTARY: "documentary",
        NEWS: "news",
        SHOW: "comedy",
        MUSIC: "music",
        SPORT: "sport",
        "1": "fiction",
        "2": "documentary",
        "3": "music",
        "4": "sport",
        "5": "news",
        "6": "comedy",
      } as Record<string, CategoryKey>
    )[key] ?? "filler"
  );
}

const NATURE_LABELS: Record<string, string> = {
  "1": "Fiction",
  "2": "Documentaire",
  "3": "Musique",
  "4": "Sport",
  "5": "Information",
  "6": "Divertissement",
  "99": "Autre",
};

const CONTAINER_KIND_LABELS: Record<string, string> = {
  "1": "Vidéo unitaire",
  "2": "Série",
  "3": "Album",
  "4": "Clip musical",
  "99": "Autre",
};

export function natureLabel(value: string | number): string {
  return NATURE_LABELS[String(value)] ?? String(value);
}

export function containerKindLabel(value: string | number): string {
  return CONTAINER_KIND_LABELS[String(value)] ?? String(value);
}
export function categoryLegend() {
  return (Object.keys(CATEGORY_COLOR) as CategoryKey[]).map((key) => ({
    key,
    ...CATEGORY_COLOR[key],
  }));
}
