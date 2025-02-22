## SpecStory

## Debugging Description Reading in Python Script (11/02/2025, 19:56:11)

_**User**_

I do 

```
python -m volante_lokalnie read_all
```

and we get

```
[02/11/25 19:55:17] INFO     2025-02-11 19:55:17,637 [INFO] Refreshing offers from website...                                                  volante_lokalnie.py:933
[02/11/25 19:55:18] INFO     2025-02-11 19:55:18,588 [INFO]                                                                                    volante_lokalnie.py:267
                             [Manual Login Required]                                                                                                                  
                             1. Please log into Allegro Lokalnie in the browser window                                                                                
                             2. Navigate to: https://allegrolokalnie.pl/konto/oferty/aktywne                                                                          
                             3. The script will continue once you're logged in and on the offers page                                                                 
                                                                                                                                                                      
                    INFO     2025-02-11 19:55:18,612 [INFO] [green]Successfully detected logged-in state!                                      volante_lokalnie.py:291
[02/11/25 19:55:19] INFO     2025-02-11 19:55:19,003 [INFO] [Site] Processing page 1 of 29...                                                  volante_lokalnie.py:946
                    INFO     2025-02-11 19:55:19,417 [INFO] [Scraper] Reading missing description for                                          volante_lokalnie.py:976
                             zmartwychwstanie-muzyka-sakralna-rosyjskie-piesni-ludowe                                                                                 
                    INFO     2025-02-11 19:55:19,418 [INFO] [Scraper] Reading details for offer                                                volante_lokalnie.py:514
                             zmartwychwstanie-muzyka-sakralna-rosyjskie-piesni-ludowe from                                                                            
                             https://allegrolokalnie.pl/oferta/zmartwychwstanie-muzyka-sakralna-rosyjskie-piesni-ludowe...                                            
[02/11/25 19:55:23] INFO     2025-02-11 19:55:23,679 [INFO] [Scraper] Reading missing description for                                          volante_lokalnie.py:976
                             muzyka-z-filmu-milczenie-owiec-the-silence-of-the-lambs                                                                                  
                    INFO     2025-02-11 19:55:23,680 [INFO] [Scraper] Reading details for offer                                                volante_lokalnie.py:514
                             muzyka-z-filmu-milczenie-owiec-the-silence-of-the-lambs from                                                                             
                             https://allegrolokalnie.pl/oferta/muzyka-z-filmu-milczenie-owiec-the-silence-of-the-lambs...                                             
[02/11/25 19:55:27] INFO     2025-02-11 19:55:27,007 [INFO] [Scraper] Reading missing description for andre-galluzzi-stadt-strand-flus-folia   volante_lokalnie.py:976
                    INFO     2025-02-11 19:55:27,009 [INFO] [Scraper] Reading details for offer andre-galluzzi-stadt-strand-flus-folia from    volante_lokalnie.py:514
                             https://allegrolokalnie.pl/oferta/andre-galluzzi-stadt-strand-flus-folia...                                                              
[02/11/25 19:55:31] INFO     2025-02-11 19:55:31,319 [INFO] [Scraper] Reading missing description for                                          volante_lokalnie.py:976
                             xavier-naidoo-zwischenspiel-alles-fuer-den-herrn-plyta-cd-nowa-folia                                                                     
                    INFO     2025-02-11 19:55:31,321 [INFO] [Scraper] Reading details for offer                                                volante_lokalnie.py:514
                             xavier-naidoo-zwischenspiel-alles-fuer-den-herrn-plyta-cd-nowa-folia from                                                                
                             https://allegrolokalnie.pl/oferta/xavier-naidoo-zwischenspiel-alles-fuer-den-herrn-plyta-cd-nowa-folia...    

```

So we're READING THE DESCRIPTION even though our `volante_lokalnie.toml` has this: 

```
["https://allegrolokalnie.pl/oferta/zmartwychwstanie-muzyka-sakralna-rosyjskie-piesni-ludowe"]
title = "Zmartwychwstanie – muzyka sakralna, rosyjskie pieśni ludowe"
price = 19.0
views = 32
listing_date = "2025-02-09T18:49:59.741654+00:00"
image_url = "https://a.allegroimg.com/s180x180b/1ea065/5ef9b71c4e63b942e7b806c620bc"
offer_type = "Kup teraz\nCena"
offer_id = "zmartwychwstanie-muzyka-sakralna-rosyjskie-piesni-ludowe"
title_new = ""
desc = "## (UWAGA Wszystkie przedmioty kupione w dniach 13 – 20 lutego 2025 zostaną wysłane 21 lutego 2025. Przepraszam za niedogodności.)\n\n## “Воскресение” / “Zmartwychwstanie”.\n\nNa grzbiecie “Вечерний звон” / “Wieczorny dzwon” Z tyłu okładki znajduje się szczegółowa lista utworów oraz informacje o albumie.\n\nTytuł albumu: “Вечерний звон” (“Those Evening Bells”)\n\nZawiera sacred and secular music (muzyka sakralna i świecka).\n\nLista utworów:\n\n— 1. “Тебе поем” – S. Rachmaninow (“We Are Singing for You”)\n\n— 2. “Единородный Сыне” – P. Turchaninow (“The Only-Begotten Son”)\n\n— 3. “На одре болести” – P. Chesnokow (“On the Disease-Bed”)\n\n— 4. “Ave Maria” – J. Arcadelt\n\n— 5. “Новелава туча златая” – P. Czajkowski (“A Golden Cloud Has Passed The Night”)\n\n— 6. “Вечер” – S. Taneyev (“Evening”)\n\nRosyjskie pieśni ludowe (Russian folk songs):\n\n— 7. “В темном лесу” (“In a Dark Wood”)\n\n— 8. “Пойду ль я, выйду ль я” (“If I Go, If I Come Out”)\n\n— 9. “Ой, перышкам кинулися” (“Oy, Perivatis Khimelnishka…”)\n\n— 10. “Вечерний звон” (“Those Evening Bells”)\n\n— 11. “Девка во саду ходила” (“A Lass Was Passing Along The Garden”)\n\n— 12. “Калинка” (“Kalinka”)\n\nInformacje o nagraniu:\n\nTverskoy Chamber Choir “Voskresenie”, Rosja\n\nDyrygent: Elena Shatunova\n\n**Nagrano w 2001 r.**\n\nNagranie zrealizowano w katedrze Św. Bonifacego w Niemczech\n\nAutor projektu: Olga Lazareva\n\nNagranie: Norbert Kinzel\n\nWydane przez ParaType Inc., 2002\n\n## album z muzyką sakralną i rosyjskimi pieśniami ludowymi, album zafoliowany"
desc_new = ""
published = false

["https://allegrolokalnie.pl/oferta/muzyka-z-filmu-milczenie-owiec-the-silence-of-the-lambs"]
title = "Muzyka z filmu Milczenie owiec / The Silence of the Lambs"
price = 89.0
views = 23
listing_date = "2025-02-09T18:37:21.127626+00:00"
image_url = "https://a.allegroimg.com/s180x180b/1ecbb4/65e1dba34d2ea0d1f576c33207a3"
offer_type = "Kup teraz\nCena"
offer_id = "muzyka-z-filmu-milczenie-owiec-the-silence-of-the-lambs"
title_new = ""
desc = "Ścieżka dźwiękowa z filmu The Silence of the Lambs \n\nKompozytor: Howard Shore\n\nPłyta nie była odtwarzana. Ma naklejkę/ plombę zabezpieczającą"
desc_new = ""
published = false

["https://allegrolokalnie.pl/oferta/andre-galluzzi-stadt-strand-flus-folia"]
title = "Andre Galluzzi – Stadt. Strand. Fluss. FOLIA"
price = 29.0
views = 14
listing_date = "2025-02-09T18:26:27.739389+00:00"
image_url = "https://a.allegroimg.com/s180x180b/1ebb28/3e4849ab4384989c2b699c081af8"
offer_type = "Kup teraz\nCena"
offer_id = "andre-galluzzi-stadt-strand-flus-folia"
title_new = ""
desc = "Mixed and compiled by Andre Galluzzi \n\nBerlin 2010"
desc_new = ""
published = false
```

Why? The `desc` fields are in the TOML. 

---

_**Assistant**_

Let me analyze the code and explain why this is happening.

The issue is in the `refresh_offers` method, specifically in this part of the code:

```python
# Only read description if it's missing or empty
# A single space desc means details have been fetched
desc = existing.desc
needs_desc = bool(not desc or desc == "")
if desc == "-":
    needs_desc = False
if needs_desc:
    logger.info(
        f"[Scraper] Reading missing description for {offer_obj.offer_id}"
    )
    self.read_offer_details(offer_obj.offer_id)
```

The logic checks if a description needs to be fetched based on two conditions:
1. If the description is None/empty (`not desc`)
2. If the description is an empty string (`desc == ""`)

Looking at your TOML file, all the descriptions are present and non-empty, so this shouldn't be triggering. Let me check the code flow more carefully...

Ah, I see the issue. The problem is in the `_extract_offer_data` method. When updating an existing offer, it's creating a new `OfferData` object first:

```python
offer = OfferData(
    title=title,
    price=price,
    views=views,
    listing_date=listing_date,
    image_url=image_url,
    offer_type=offer_type,
    offer_id=offer_id,
)
```

Then it tries to update the existing offer:

```python
# Update existing offer while preserving additional fields
if offer_link in self.db.data:
    existing = self.db.data[offer_link]
    # Update only basic fields
    existing.title = offer.title
    existing.price = offer.price
    existing.views = offer.views
    self.db.data[offer_link] = existing
```

Let me fix this by editing the file to properly preserve all fields when updating existing offers:

---

_****_

```diff
                  logger.debug(f"[Scraper] Type: {offer_type}")
  
-             offer = OfferData(
-                 title=title,
-                 price=price,
-                 views=views,
-                 listing_date=listing_date,
-                 image_url=image_url,
-                 offer_type=offer_type,
-                 offer_id=offer_id,
-             )
- 
-             # Update existing offer while preserving additional fields
-             if offer_link in self.db.data:
-                 existing = self.db.data[offer_link]
-                 # Update only basic fields
-                 existing.title = offer.title
-                 existing.price = offer.price
-                 existing.views = offer.views
-                 self.db.data[offer_link] = existing
-             else:
+             if offer_link in self.db.data:
+                 existing = self.db.data[offer_link]
+                 # Update only basic fields while preserving all others
+                 existing.title = title
+                 existing.price = price
+                 existing.views = views
+                 existing.listing_date = listing_date
+                 existing.image_url = image_url
+                 existing.offer_type = offer_type
+                 self.db.data[offer_link] = existing
+                 if self.verbose:
+                     logger.debug(f"[Scraper] Updated existing offer {offer_id}")
+                 return offer_link, existing
+             else:
+                 # New offer: initialize with empty edits
+                 offer = OfferData(
+                     title=title,
+                     price=price,
+                     views=views,
+                     listing_date=listing_date,
+                     image_url=image_url,
+                     offer_type=offer_type,
+                     offer_id=offer_id,
+                 )
                  self.db.data[offer_link] = offer
-             self.db.save()
- 
-             return offer_link, offer
+                 self.db.save()
+                 if self.verbose:
+                     logger.debug(f"[Scraper] Created new offer {offer_id}")
+                 return offer_link, offer
  
          except Exception as e:
```

---

_****_



The issue was that the code was creating a new `OfferData` object first and then trying to update only some fields from it. This meant that when updating an existing offer, we were first creating a new `OfferData` instance (which has empty description fields) and then only copying over basic fields like title, price, and views.

I've fixed it by:
1. First checking if the offer exists
2. If it does, directly updating the basic fields while preserving all other fields (like descriptions)
3. Only creating a new `OfferData` instance for truly new offers

This should prevent the unnecessary description fetching for offers that already have descriptions in the TOML file. Try running the command again and it should no longer try to re-fetch descriptions for offers that already have them.

---

_**User**_

ok, this looks fixed! 

---

_**Assistant**_

Yes! The fix looks good. Now when updating existing offers, we:

1. First check if the offer exists in the database
2. If it does, we directly update only the basic fields (title, price, views, listing_date, image_url, offer_type) on the existing object
3. Most importantly, we preserve all other fields including `desc`, `desc_new`, `title_new`, and `published` status
4. Only for completely new offers do we create a fresh `OfferData` instance with empty fields

This should prevent the unnecessary description fetching we were seeing before, since the descriptions will be preserved from the TOML file for existing offers.

Would you like to test it again with the `read_all` command to confirm it's working as expected?

---



---

