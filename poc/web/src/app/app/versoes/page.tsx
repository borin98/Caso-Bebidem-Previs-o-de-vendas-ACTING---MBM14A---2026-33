import { VersionsView } from "@/components/versions-view";

export default async function VersionsPage({ searchParams }: PageProps<"/app/versoes">) {
  const params = await searchParams;
  const base = typeof params.base === "string" && params.base !== "" ? params.base : null;
  const target = typeof params.alvo === "string" && params.alvo !== "" ? params.alvo : null;
  return <VersionsView base={base} target={target} />;
}
