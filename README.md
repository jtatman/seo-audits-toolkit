<p align="center"><img src="./docs/images/OSAT.png" width="180px" /></p>


# Open source Audits Toolkit

**OSAT** is a collection of tools created help you in your quest for a better website. All of these tools have been grouped into a single web app.

I've grown tired of SEO agencies making us pay hundreds of euros for simple tools. I decided to develop **OSAT** to help users find issues on their website and increase their SEO for free. 

<p align="center"><img src="./docs/images/osat-demo.gif" width="700px" /></p>

## Why you need it


- It's **free**, easy and open source. 
- It has a growing list of features
- It's easy to install

## Features

- **Authentification** - A fully featured authentification system for the front & back
- **RBAC/Organizations** - Create different organizations and give different access to each org to your users.
- **Lighthouse Score** -  Run [Lighthouse](https://developers.google.com/web/tools/lighthouse) Audits and keep track of your scores
- **Keywords Finder** - Find all the keywords of an article.
- **Extract Headers/Links/Images** - Easily extract all the links on your website and their status codes, the headers of a page and all the images.
- **Sitemap Extractor** - Extract all the urls of a website from its sitemap
- **Internal Links Graph** - Crawl a site and visualize how its pages link to each other
- **Summarizer** - Summarize any text from any length. Awesome for excerpt !
- **Security Audit** - Audit Headers, Redirect, etc to make sure your website is secure, powered by [MDN's HTTP Observatory](https://developer.mozilla.org/en-US/observatory).

## Demo

Go to [demo.primates.dev](https://demo.primates.dev) <br>
**Login**: demo <br>
**Password**: demodemo <br>

Admin part is [api.primates.dev/admin](https://api.primates.dev/admin)

*(That's the original project's own hosted demo - unrelated to whatever you deploy from this fork.)*

## Installation

Requires Docker and Docker Compose. There are no pre-built images to pull for
this fork - always build locally:

```Bash
git clone https://github.com/StanGirard/seo-audits-toolkit
cd seo-audits-toolkit
cp .env-example .env
docker compose build
docker compose up -d
```

Edit `.env` first if you want anything other than the defaults - at minimum,
set a real `SECRET_KEY` (the example one is a public placeholder, fine for
local use only) and a real `POSTGRES_PASSWORD`.

Init the project - creates an `admin`/`admin` superuser, a demo organization,
and the recurring Lighthouse/Security crawl schedules. Safe to run more than
once:

```Bash
docker exec -it osat-server python manage.py seed_demo_data
```

Pass `--username`, `--password`, `--email`, `--org-name`, or `--org-url` to
override any of the defaults.

## Dashboard

You can access the dashboard by going to [localhost:3000](http://localhost:3000)

**Login**: admin
**Password**: admin

## Config

`.env` (copied from `.env-example`) controls everything - database
credentials, Redis/Postgres versions, Node version, Django settings, etc.
Re-run `docker compose up -d` after changing it.

## Configuration

`seed_demo_data` (above) already creates one organization and adds the admin
user to it, so most people can skip straight to using the app. To add more:

### Create an organization

Go to `Org -> Organization` in the admin dashboard and create a new one. You
can create as many as you want - organizations implement RBAC in this
project, scoping what a user can see to their own org(s). Quick link:
[http://localhost:8000/admin/org/website/](http://localhost:8000/admin/org/website/)

### Add a user to an organization

Go to `Organizations -> Organizations Users` and add your users to the
organization you want. [http://localhost:8000/admin/organizations/organizationuser/](http://localhost:8000/admin/organizations/organizationuser/)

## Useful Links

- **Webapp** [http://localhost:3000](http://localhost:3000)
- **Admin Dashboard** [http://localhost:8000/admin](http://localhost:8000/admin)
- **Swagger like interface** [http://localhost:8000](http://localhost:8000)


## Contributions

Please feel free to add any contribution.
If you've been working on a script that could be integrated in this app. Please feel free to do it. Don't hesitate to open issues to ask questions. I've tried to document the code as much as I could to ease the integration

### Backend 
You can just add a django module and I'll take care of intregrating it in the front.
### Frontend
The front-end is built with [React Admin](https://marmelab.com/react-admin/) v5, on Vite. If you want to help me improve the UI or add new functionnalites, please feel free to contribute.

### Stack at a glance

| | Version |
|---|---|
| Python | 3.12 |
| Django | 5.2 LTS |
| Node | 22 |
| React / React Admin | 19 / 5 |
| Frontend build | Vite 6 + Vitest |

See `CLAUDE.md` for the full modernization history and current project
conventions (this project tracks tasks with [beads](https://github.com/gastownhall/beads)
and project memory with mnemoria - run `bd ready` / `mnemoria search "<query>"`
if you have those installed and want the full history behind a decision).

## Disclaimers

I'm not a python nor a frontend developer.
