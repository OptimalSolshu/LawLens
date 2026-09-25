import { Layout, Panel, TwoColumns } from "./components/Layout";
import { ArticleList } from "./features/search/ArticleList";
import { LawPanel } from "./features/search/LawPanel";
import { LawSearch } from "./features/search/LawSearch";
import { useSelection } from "./lib/url";

export default function App() {
  const [sel, update] = useSelection();

  return (
    <Layout view={sel.view} onNavigate={(view) => update({ view })}>
      {sel.view === "search" ? (
        <TwoColumns
          left={
            <>
              <Panel>
                <LawSearch selectedLaw={sel.law} onSelect={(law) => update({ law, article: null })} />
              </Panel>
              {sel.law && (
                <Panel>
                  <ArticleList
                    key={sel.law}
                    lawId={sel.law}
                    selectedArticle={sel.article}
                    onSelect={(article) => update({ article })}
                  />
                </Panel>
              )}
            </>
          }
          right={
            sel.law ? (
              <LawPanel lawId={sel.law} articleId={sel.article} />
            ) : (
              <Panel>
                <p className="text-ink-2">
                  Хуулийн холбоосыг харахын тулд зүүн талын хайлтаас хууль сонгоно уу.
                </p>
              </Panel>
            )
          }
        />
      ) : (
        <Panel>
          <p className="text-ink-2">Энэ хэсэг боловсруулалтын шатанд байна.</p>
        </Panel>
      )}
    </Layout>
  );
}
