import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Boxes,
  BrainCircuit,
  BriefcaseBusiness,
  Code2,
  Compass,
  Github,
  Linkedin,
  MapPin,
  Music2,
  Network,
  Radio,
} from "lucide-react";
import Head from "next/head";
import Image from "next/image";
import Link from "next/link";

import { MotionDiv, MotionLink, Reveal, Stagger, StaggerItem } from "../components/Motion";
import { SiteShell } from "../components/SiteShell";

const capabilities = [
  {
    icon: BrainCircuit,
    title: "AI engineering",
    text: "LLM applications, agentic workflows and model-powered tools designed around measurable, real-world outcomes.",
    accent: "mint",
  },
  {
    icon: Code2,
    title: "Product engineering",
    text: "Web applications and product experiences shaped from the interface through to the underlying architecture.",
    accent: "blue",
  },
  {
    icon: Network,
    title: "Systems & backends",
    text: "Reliable APIs, integrations, data pipelines and infrastructure designed for real operational constraints.",
    accent: "peach",
  },
];

const projects = [
  {
    title: "Pharma Portal",
    label: "Operational intelligence",
    text: "A pharmacy reporting platform connecting dispensing and POS systems to clear, actionable store insights.",
    image: "/pharma-portal-landing.png",
    href: "https://www.pharmaportal.com.au",
    tone: "project-blue",
  },
  {
    title: "Shreem",
    label: "Pharmacy marketplace",
    text: "A supplier marketplace that simplifies pharmacy purchasing, pricing and multi-supplier ordering.",
    image: "/shreem-landing.png",
    href: "https://www.shreem.au",
    tone: "project-mint",
  },
];

const skillGroups = [
  { label: "Intelligence", skills: ["AI workflows", "LangChain", "LLM APIs"] },
  { label: "Applications", skills: ["TypeScript", "Next.js", "Python", "FastAPI"] },
  { label: "Data & delivery", skills: ["MongoDB", "Docker", "AWS"] },
];

export default function HomePage() {
  return (
    <SiteShell>
      <Head>
        <title>Jack Hales — AI Engineer</title>
        <meta name="description" content="Australian AI engineer building intelligent workflows, useful products and dependable technical systems." />
      </Head>

      <section className="home-hero">
        <Reveal className="hero-copy">
          <p className="eyebrow">AI engineer · Systems thinker</p>
          <h1 className="display-title">
            I build useful systems from <span className="accent">complex ideas.</span>
          </h1>
          <p className="lead">
            I&apos;m Jack, a language-agnostic AI engineer focused on intelligent workflows, product systems and difficult technical problems. I choose the tools that fit the work, then turn ambiguity into dependable software people can actually use.
          </p>
          <div className="hero-actions">
            <Link href="/background-and-experience" className="button button-dark">
              Explore my work <ArrowRight size={16} />
            </Link>
            <a href="mailto:me@jackhales.com" className="button button-outline">Email me</a>
          </div>
        </Reveal>

        <Reveal className="profile-composition" delay={0.12}>
          <MotionDiv className="profile-card card" whileHover={{ y: -6, rotate: -0.4 }} transition={{ type: "spring", stiffness: 260, damping: 22 }}>
            <div className="profile-image-wrap">
              <Image src="/jack-hales-picture-harbour.jpg" fill sizes="(max-width: 768px) 80vw, 400px" alt="Jack Hales at Sydney Harbour" className="profile-image" priority />
              <span className="profile-location"><MapPin size={13} /> Australia</span>
            </div>
            <div className="profile-card-copy">
              <div>
                <p className="eyebrow">Currently exploring</p>
                <h2>AI flows, intelligent tools & prime-number research.</h2>
              </div>
              <Link href="/article/prime-number-research-2024" aria-label="Read prime number research" className="round-link"><ArrowUpRight size={18} /></Link>
            </div>
          </MotionDiv>
        </Reveal>
      </section>

      <Reveal>
        <Link href="/article/prime-number-research-2024" className="research-strip card card-interactive">
          <span className="research-icon"><BrainCircuit size={21} /></span>
          <span className="research-copy">
            <small>Active research</small>
            <strong>Experimenting with the patterns and chaos of prime numbers</strong>
          </span>
          <span className="research-action">Read the journal <ArrowUpRight size={15} /></span>
        </Link>
      </Reveal>

      <section className="section-block">
        <Reveal className="section-heading">
          <div><p className="eyebrow">What I do</p><h2>Across the whole system.</h2></div>
          <p>I&apos;m most useful where product thinking, technical depth and messy real-world data meet.</p>
        </Reveal>
        <Stagger className="capability-grid">
          {capabilities.map(({ icon: Icon, title, text, accent }) => (
            <StaggerItem key={title}>
              <MotionDiv className="capability-card card" whileHover={{ y: -7 }} transition={{ type: "spring", stiffness: 280, damping: 22 }}>
                <span className={`icon-tile icon-${accent}`}><Icon size={21} /></span>
                <span className="card-index">0{capabilities.findIndex((item) => item.title === title) + 1}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </MotionDiv>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <section className="section-block">
        <Reveal className="section-heading">
          <div><p className="eyebrow">Selected work</p><h2>Products built for real operations.</h2></div>
          <Link href="/background-and-experience" className="text-link">Full experience <ArrowRight size={15} /></Link>
        </Reveal>
        <Stagger className="project-grid">
          {projects.map((project) => (
            <StaggerItem key={project.title}>
              <MotionLink href={project.href} target="_blank" rel="noreferrer" className={`project-card card ${project.tone}`} whileHover={{ y: -7 }}>
                <div className="project-visual">
                  <Image src={project.image} fill sizes="(max-width: 768px) 100vw, 50vw" alt={`${project.title} product interface`} />
                </div>
                <div className="project-copy">
                  <p className="eyebrow">{project.label}</p>
                  <div className="project-title-row"><h3>{project.title}</h3><ArrowUpRight size={19} /></div>
                  <p>{project.text}</p>
                </div>
              </MotionLink>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <section className="section-block">
        <Reveal className="section-heading bento-section-heading">
          <div><p className="eyebrow">Working set</p><h2>Tools, interests & places to follow.</h2></div>
          <p>A compact view of what I build with, what keeps me curious and where I share the work.</p>
        </Reveal>

        <div className="bento-grid">
          <Reveal className="bento-card card bento-interests">
            <div className="bento-card-header">
              <span className="icon-tile icon-peach"><Compass size={21} /></span>
              <p className="eyebrow">Beyond the screen</p>
            </div>
            <h3>Good software starts with a wider world.</h3>
            <div className="interest-list">
              <span><BookOpen size={18} /> History & reading</span>
              <span><Music2 size={18} /> Music</span>
              <span><MapPin size={18} /> Travel & bush walks</span>
            </div>
            <Link href="/software-engineers-guide-exploring-oman-top-travel-tips-itinerary" className="bento-card-link">Read my Oman guide <ArrowRight size={15} /></Link>
          </Reveal>

          <Reveal className="bento-card card bento-social" delay={0.08}>
            <div className="bento-card-header">
              <span className="icon-tile icon-mint"><Radio size={21} /></span>
              <p className="eyebrow">Find me online</p>
            </div>
            <h3>Follow the work as it develops.</h3>
            <div className="social-links">
              <a href="https://www.linkedin.com/in/jackhales/" target="_blank" rel="noreferrer"><Linkedin size={20} /><span>LinkedIn<small>Professional updates</small></span><ArrowUpRight size={16} /></a>
              <a href="https://github.com/halesyy/" target="_blank" rel="noreferrer"><Github size={20} /><span>GitHub<small>Code & experiments</small></span><ArrowUpRight size={16} /></a>
              <Link href="/articles"><BriefcaseBusiness size={20} /><span>Writing<small>Research & ideas</small></span><ArrowUpRight size={16} /></Link>
            </div>
          </Reveal>

          <Reveal className="bento-card card bento-skills" delay={0.16}>
            <div className="bento-skills-copy">
              <div className="bento-card-header">
                <span className="icon-tile icon-blue"><Boxes size={21} /></span>
                <p className="eyebrow">Technical toolkit</p>
              </div>
              <h3>Tools follow the problem.</h3>
              <p className="bento-body">A pragmatic mix of typed application development, data systems, cloud platforms and automation.</p>
            </div>
            <div className="skill-groups">
              {skillGroups.map((group) => (
                <div className="skill-group" key={group.label}>
                  <p>{group.label}</p>
                  <div className="tag-list">{group.skills.map((skill) => <span className="tag" key={skill}>{skill}</span>)}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>
    </SiteShell>
  );
}
