# Why web apps

## The comparison nobody shows you

| | Native iOS app | Home-screen web app |
|---|---|---|
| Developer account | 99 USD/year | none |
| Toolchain | Xcode, a Mac, signing certificates | a text editor |
| Shipping a change | build, sign, upload, review (hours to days) | save the file |
| Review | Apple decides | nobody |
| Store cut | up to 30% | none |
| Works on Android too | no | yes |
| Time to first working version | days | an afternoon |

For a personal tool reached over a private network, the native column buys you nothing you need and
costs you everything.

## What you genuinely give up

Discovery, Shortcuts intents, widgets, Live Activities, share-sheet targets, background execution,
and straightforward push. See `03-iphone-gotchas.md` for the full list and the audio rules.

If any of those are load-bearing for what you are building, build a real app. If, like almost every
tool on `IDEAS.md`, you want a thumb-sized window onto something already running on a machine you
own, this is strictly better.

## Where it started

> **Fred:** "How hard was it for you to do iPhone apps? I've not even ventured into the iPhone app
> creation."
>
> **A friend who builds iPhone apps:** "Honestly, it's just a web app... You just open it once in
> Safari, and then share and add to Home Screen, and that's all you have to do."
>
> **Fred:** "You're skipping 90% of the hard shit and going straight to the benefit. That's what I
> learned tonight."
