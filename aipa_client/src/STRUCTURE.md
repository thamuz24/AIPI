# Source Structure

- `src/app`: app shell, route composition, and route guards.
- `src/features`: domain features grouped by business area.
- `src/shared`: reusable cross-feature modules (api, config, services).

## Feature Groups

- `features/auth`
  - `pages`: login/register/recovery screens.
  - `context`: authentication state and actions.
- `features/home`
  - `pages`: home/chat screen.
  - `model`: config for anime model asset path.
- `features/user`
  - `pages`: user profile/settings screen.

## Shared Modules

- `shared/api`: HTTP client and API adapters.
- `shared/config`: environment config.
- `shared/services`: helpers for storage and error mapping.

## Anime Model Asset

- Put your character image at:
  - `public/assets/anime-model/character.png`
- The app reads this path from:
  - `src/features/home/model/animeModelConfig.js`
