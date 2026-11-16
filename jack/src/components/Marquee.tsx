import { useEffect, useRef, useState } from 'react';

const B = 'https://motionsites.ai/assets/';
const IMAGES = ['hero-space-voyage-preview-eECLH3Yc','hero-codenest-preview-Cgppc2qV','hero-vex-ventures-preview-BczMFIiw','hero-stellar-ai-v2-preview-DjvxjG3C','hero-asme-preview-B_nGDnTP','hero-transform-data-preview-Cx5OU29N','hero-vitara-preview-Cjz2QYyU','hero-terra-preview-BFjrCr7T','hero-skyelite-preview-DHaZIgUv','hero-aethera-preview-DknSlcTa','hero-designpro-preview-D8c5_een','hero-stellar-ai-preview-D3HL6bw1','hero-xportfolio-preview-D4A8maiC','hero-orbit-web3-preview-BXt4OttD','hero-nexora-preview-cx5HmUgo','hero-evr-ventures-preview-DZxeVFEX','hero-planet-orbit-preview-DWAP8Z1P','hero-new-era-preview-CocuDUm9','hero-wealth-preview-B70idl_u','hero-luminex-preview-CxOP7ce6','hero-celestia-preview-0yO3jXO8'].map((n) => `${B}${n}.gif`);

const row1 = [...IMAGES.slice(0, 11), ...IMAGES.slice(0, 11), ...IMAGES.slice(0, 11)];
const row2 = [...IMAGES.slice(11), ...IMAGES.slice(11), ...IMAGES.slice(11)];

function Row({ items, transform }: { items: string[]; transform: string }) {
  return (
    <div className="flex gap-3 w-max" style={{ transform, willChange: 'transform' }}>
      {items.map((src, i) => (
        <img key={i} src={src} alt="" loading="lazy" className="rounded-2xl object-cover shrink-0" style={{ width: 420, height: 270 }} />
      ))}
    </div>
  );
}

export default function MarqueeSection() {
  const ref = useRef<HTMLElement>(null);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const el = ref.current; if (!el) return;
      const top = el.getBoundingClientRect().top + window.scrollY;
      setOffset((window.scrollY - top + window.innerHeight) * 0.3);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return (
    <section ref={ref} className="pt-24 sm:pt-32 md:pt-40 pb-10 flex flex-col gap-3 overflow-hidden" style={{ background: '#0C0C0C' }}>
      <Row items={row1} transform={`translateX(${offset - 200}px)`} />
      <Row items={row2} transform={`translateX(${-(offset - 200)}px)`} />
    </section>
  );
}
