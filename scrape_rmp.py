import os
import requests
import json
import time

url = "https://www.ratemyprofessors.com/graphql"
headers = {
    "Authorization": "Basic d2ViY2xpZW50OndlYmNsaWVudA==",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

school_id = "U2Nob29sLTIyNg=="  # Hunter College school ID on RMP
professors = [
    "Eric Schweitzer",
    "Tiziana Ligorio",
    "Melissa Lynch",
    "Saad Mneimneh",
    "Susan Epstein",
    "Pavel Shostak",
    "Mike Zamansky",
    "Katherine St. John",
    "Stewart Weiss",
    "Ioannis Stamos"
]

output_dir = "documents"
os.makedirs(output_dir, exist_ok=True)

search_query = """
query TeacherSearchQuery($query: TeacherSearchQuery!) {
  newSearch {
    teachers(query: $query) {
      edges {
        node {
          id
          firstName
          lastName
          avgRating
          numRatings
        }
      }
    }
  }
}
"""

ratings_query = """
query TeacherRatingsQuery($id: ID!, $count: Int!) {
  node(id: $id) {
    ... on Teacher {
      id
      firstName
      lastName
      avgRating
      numRatings
      department
      wouldTakeAgainPercent
      avgDifficulty
      ratings(first: $count) {
        edges {
          node {
            id
            comment
            date
            class
            difficultyRating
            clarityRating
            helpfulRating
            ratingTags
          }
        }
      }
    }
  }
}
"""

def search_professor(name):
    # Try searching for the full name first
    variables = {
        "query": {
            "text": name,
            "schoolID": school_id
        }
    }
    try:
        r = requests.post(url, json={"query": search_query, "variables": variables}, headers=headers, timeout=10)
        if r.status_code == 200:
            edges = r.json().get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
            for edge in edges:
                node = edge["node"]
                # Match the last name to avoid false matches
                last_name_target = name.split()[-1].lower()
                if last_name_target in node["lastName"].lower():
                    return node["id"]
        # Fallback to search just by last name if full name search yields nothing
        last_name = name.split()[-1]
        variables["query"]["text"] = last_name
        r = requests.post(url, json={"query": search_query, "variables": variables}, headers=headers, timeout=10)
        if r.status_code == 200:
            edges = r.json().get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
            for edge in edges:
                node = edge["node"]
                first_name_target = name.split()[0].lower()
                if first_name_target in node["firstName"].lower():
                    return node["id"]
    except Exception as e:
        print(f"Error searching for {name}: {e}")
    return None

def fetch_and_save_reviews(prof_name, prof_id):
    variables = {
        "id": prof_id,
        "count": 25  # Fetch top 25 reviews to ensure deep context coverage
    }
    try:
        r = requests.post(url, json={"query": ratings_query, "variables": variables}, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"Failed to fetch reviews for {prof_name}")
            return
        
        data = r.json().get("data", {}).get("node", {})
        if not data:
            print(f"No data returned for {prof_name}")
            return
        
        dept = data.get("department", "Computer Science")
        overall = data.get("avgRating", 0.0)
        take_again = data.get("wouldTakeAgainPercent", 0.0)
        diff = data.get("avgDifficulty", 0.0)
        num_ratings = data.get("numRatings", 0)
        
        # Clean take_again percent
        take_again_str = f"{take_again:.1f}%" if take_again > 0 else "N/A"
        
        # Format the text content
        content = []
        content.append(f"Professor: {prof_name}")
        content.append("School: Hunter College")
        content.append(f"Department: {dept}")
        content.append(f"Overall Quality: {overall} / 5.0")
        content.append(f"Would Take Again: {take_again_str}")
        content.append(f"Difficulty: {diff} / 5.0")
        content.append(f"Total Ratings: {num_ratings}")
        content.append("")
        
        ratings = data.get("ratings", {}).get("edges", [])
        for edge in ratings:
            node = edge["node"]
            date_raw = node.get("date", "")
            date_clean = date_raw.split()[0] if date_raw else "N/A"
            course = node.get("class", "N/A")
            comment = node.get("comment", "").strip()
            # Calculate rating (average of helpfulness and clarity)
            helpful = node.get("helpfulRating", 0.0)
            clarity = node.get("clarityRating", 0.0)
            rating = (helpful + clarity) / 2.0
            
            diff_rating = node.get("difficultyRating", 0.0)
            tags = node.get("ratingTags", "").replace("--", ", ")
            
            content.append("---")
            content.append(f"Date: {date_clean}")
            content.append(f"Course: {course}")
            content.append(f"Rating: {rating:.1f}")
            content.append(f"Difficulty: {diff_rating:.1f}")
            content.append(f"Comment: {comment}")
            content.append(f"Tags: {tags if tags else 'None'}")
            content.append("")
            
        # Write to file
        filename = prof_name.lower().replace(".", "").replace(" ", "_") + ".txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        print(f"Saved {len(ratings)} real reviews for {prof_name} to {filepath}")
        
    except Exception as e:
        print(f"Error fetching reviews for {prof_name}: {e}")

print("Starting Rate My Professors Scraper for Hunter College CS...")
for name in professors:
    print(f"Processing: {name}...")
    prof_id = search_professor(name)
    if prof_id:
        fetch_and_save_reviews(name, prof_id)
    else:
        print(f"Could not find professor ID for {name}")
    time.sleep(1)  # Respectful rate limiting delay
print("Finished scraping reviews!")
