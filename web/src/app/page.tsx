import SmoothScroll from "@/components/SmoothScroll";
import Hero from "@/components/Hero/Hero";

export default function Home() {
  return (
    <SmoothScroll>
      <main>
        <Hero />
        {/* 后续模块将在此处添加 */}
      </main>
    </SmoothScroll>
  );
}
