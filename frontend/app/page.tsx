import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Dna, Zap, BarChart3 } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold tracking-tight mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Protein Flexibility Analysis Platform
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 mb-8">
            タンパク質の揺らぎを高速解析。UniProt ID
            から残基ごとの柔軟性スコアを可視化します。
          </p>
          <Link href="/analyze">
            <Button size="lg" className="gap-2">
              <Dna className="w-5 h-5" />
              解析を開始
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-8">
          <Card className="border-2 hover:border-blue-500 transition-colors">
            <CardHeader>
              <Zap className="w-12 h-12 mb-4 text-blue-600" />
              <CardTitle>高速解析</CardTitle>
              <CardDescription>
                NumPy ベクトル化により、数百構造の解析を数秒で完了
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
                <li>✓ 自動 PDB 取得</li>
                <li>✓ 残基ミスマッチ除外</li>
                <li>✓ 404 エラー自動スキップ</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-2 hover:border-purple-500 transition-colors">
            <CardHeader>
              <Dna className="w-12 h-12 mb-4 text-purple-600" />
              <CardTitle>UniProt 統合</CardTitle>
              <CardDescription>
                UniProt ID を入力するだけで、全 PDB 構造を自動解析
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
                <li>✓ Inactive ID 自動解決</li>
                <li>✓ 最大 100 構造まで対応</li>
                <li>✓ DSA・UMF 統合解析</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-2 hover:border-green-500 transition-colors">
            <CardHeader>
              <BarChart3 className="w-12 h-12 mb-4 text-green-600" />
              <CardTitle>3D 可視化</CardTitle>
              <CardDescription>
                残基ごとの flex_score を Mol* Viewer で直感的に表示
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
                <li>✓ インタラクティブ操作</li>
                <li>✓ リアルタイムハイライト</li>
                <li>✓ 統計グラフ連動</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <Card className="max-w-2xl mx-auto bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-2">
          <CardHeader>
            <CardTitle className="text-3xl">今すぐ解析を始める</CardTitle>
            <CardDescription className="text-lg">
              UniProt ID を用意してください
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/analyze">
              <Button size="lg" className="gap-2">
                <Dna className="w-5 h-5" />
                解析ページへ
              </Button>
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
