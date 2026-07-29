import { ArrowUpRight, Compass, FileLock2, PenLine, ScrollText, Sparkles, SplitSquareHorizontal, UserRound } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { Reveal, Stagger, StaggerItem } from "../components/Motion";
import { SiteShell } from "../components/SiteShell";

const mine = [
  "The question, and why it is worth asking",
  "The research, the reading and the experiments",
  "The argument, the structure and the conclusions",
  "Every judgement about what is true and what is worth saying",
  "The final read, the edits and the decision to publish",
];

const assisted = [
  "Turning notes and transcripts into first-draft prose",
  "Breaking a sprawling idea into sections that hold together",
  "Tightening paragraphs that say the same thing twice",
  "Titles, summaries and metadata",
];

const never = [
  "Deciding what I think",
  "Inventing research, results or sources",
  "Publishing anything — I am the only one who can do that",
];

const parallel = [
  { icon: <Compass size={20} />, tone: "icon-blue", label: "Company building", copy: "The work that pays for the curiosity, and the one with real deadlines attached." },
  { icon: <SplitSquareHorizontal size={20} />, tone: "icon-mint", label: "Prime number research", copy: "A long-running exploration of structure and pattern that I have never been able to leave alone." },
  { icon: <Sparkles size={20} />, tone: "icon-peach", label: "Experiments in AI", copy: "Agents, tooling and evaluation. Mostly built to find out where the idea breaks." },
];

export default function AiAssistedPage() {
  return (
    <SiteShell>
      <Head>
        <title>AI-assisted writing — Jack Hales</title>
        <meta
          name="description"
          content="What the AI-assisted badge on Jack Hales' articles means: directed and original content, where AI helps with the writing and the breakdown, and the research and conclusions stay mine."
        />
        <link rel="canonical" href="https://jackhales.com/ai-assisted" />
        <meta property="og:type" content="article" />
        <meta property="og:title" content="AI-assisted writing — Jack Hales" />
        <meta
          property="og:description"
          content="Directed and original content. AI assists with the writing and the breakdown; the ideas, research and conclusions are mine."
        />
      </Head>

      <Reveal className="page-hero page-hero-row">
        <div>
          <p className="eyebrow eyebrow-icon"><Sparkles size={13} /> What the badge means</p>
          <h1 className="display-title">Directed by me. <span className="accent">Written with help.</span></h1>
        </div>
        <p className="lead page-side-lead">
          Some articles here carry an AI-assisted badge. It means the thinking, the research and the conclusions are mine, and that
          AI helped me get them out of my head and onto the page.
        </p>
      </Reveal>

      <section className="ai-split">
        <Reveal className="ai-panel card">
          <span className="icon-tile icon-blue"><UserRound size={21} /></span>
          <p className="eyebrow">Always mine</p>
          <h2>The part that matters.</h2>
          <ul>{mine.map((item) => <li key={item}>{item}</li>)}</ul>
        </Reveal>
        <Reveal className="ai-panel card" delay={0.08}>
          <span className="icon-tile icon-mint"><PenLine size={21} /></span>
          <p className="eyebrow">Where AI helps</p>
          <h2>The drafting and the shape.</h2>
          <ul>{assisted.map((item) => <li key={item}>{item}</li>)}</ul>
        </Reveal>
        <Reveal className="ai-panel card ai-panel-never" delay={0.16}>
          <span className="icon-tile icon-peach"><FileLock2 size={21} /></span>
          <p className="eyebrow">Never</p>
          <h2>The lines it does not cross.</h2>
          <ul>{never.map((item) => <li key={item}>{item}</li>)}</ul>
        </Reveal>
      </section>

      <section className="section-block">
        <Reveal className="section-heading">
          <div><p className="eyebrow">Why</p><h2>More curiosity than hours.</h2></div>
          <p>I am running several things in parallel. The ideas keep arriving whether or not there is an evening free to write them up.</p>
        </Reveal>
        <Stagger className="integration-grid">
          {parallel.map((item) => (
            <StaggerItem key={item.label}>
              <div className="integration-card card">
                <span className={`icon-tile ${item.tone}`}>{item.icon}</span>
                <h3>{item.label}</h3>
                <p>{item.copy}</p>
              </div>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <Reveal className="ai-quote card">
        <span className="icon-tile icon-blue"><ScrollText size={21} /></span>
        <p className="eyebrow">An old solution to the same problem</p>
        <h2>Pliny travelled with a writer at his side.</h2>
        <p className="ai-quote-lead">
          Pliny the Elder produced an encyclopaedia of the known world while holding public office and commanding a fleet. His nephew
          explained how: he refused to let any hour go unused, and he never travelled without someone to take down what he said.
        </p>
        <blockquote className="ai-quote-block">
          <p lang="la">
            In itinere quasi solutus ceteris curis, huic uni vacabat: ad latus notarius cum libro et pugillaribus, cuius manus hieme
            manicis muniebantur, ut ne caeli quidem asperitas ullum studii tempus eriperet.
          </p>
          <p>
            On the road, as though released from every other concern, he gave himself to this alone: at his side a shorthand writer with
            book and tablets, whose hands were wrapped against the cold in winter, so that not even bitter weather could steal an hour
            of study.
          </p>
          <cite>Pliny the Younger, <em>Letters</em> 3.5 — my rendering of the Latin</cite>
        </blockquote>
        <p>
          He was carried through Rome in a chair for the same reason, and once scolded his nephew for going on foot: those hours could
          have been spent. It is an extreme worth disagreeing with — I would rather keep the walk. But the underlying problem is
          familiar. The bottleneck was never the thinking. It was the transcription.
        </p>
        <p className="ai-quote-close">
          A model is a poor substitute for a Roman secretary in most respects and a much better one in a few. It listens to a
          half-formed idea at eleven at night, gives it a shape I can argue with, and asks nothing of anyone else&apos;s evening.
        </p>
      </Reveal>

      <section className="section-block">
        <Reveal className="section-heading">
          <div><p className="eyebrow">How it actually works</p><h2>Drafts only. I publish.</h2></div>
          <p>The badge is not a promise I make. It is recorded by the system that does the assisting.</p>
        </Reveal>
        <Stagger className="ai-mechanics">
          {[
            { step: "01", title: "A scoped key", copy: "Writing tools reach the site through an API key I generate myself. It can read everything and edit drafts. It cannot publish, and it cannot touch an article that is already live." },
            { step: "02", title: "The badge is automatic", copy: "Every edit made with that key marks the article as AI-assisted. The key cannot set the flag or clear it, so assistance cannot quietly go unrecorded." },
            { step: "03", title: "Then I read it properly", copy: "Nothing reaches this site without me reading it end to end, changing what is wrong, and choosing to publish it. An article without the badge was written the long way." },
          ].map((item) => (
            <StaggerItem key={item.step}>
              <div className="ai-step card">
                <span className="ai-step-number">{item.step}</span>
                <h3>{item.title}</h3>
                <p>{item.copy}</p>
              </div>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <Reveal className="ai-closing card">
        <p className="eyebrow">The honest version</p>
        <h2>I would rather publish the thinking than protect the byline.</h2>
        <p>
          There is a version of this where I write everything myself and most of it never gets written. The research still happens
          either way — it just stays in notebooks and half-finished repositories. This is the trade I have chosen, and the badge is
          there so you can weigh it yourself.
        </p>
        <Link href="/articles" className="button button-dark">Read the writing <ArrowUpRight size={16} /></Link>
      </Reveal>
    </SiteShell>
  );
}
