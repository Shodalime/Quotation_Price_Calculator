# 🧮 Price Calculator Application

A custom **Price Calculator** application built in **Python**, designed to automate intricate pricing logic for the **abrasive manufacturing industry**.  
The app uses both **SQLite (local)** and **Turso (cloud)** databases to store and manage product data efficiently, ensuring **real-time synchronization** and **global accessibility**.

---

## 🚀 Overview

The **Price Calculator** automates complex pricing workflows by integrating product data such as:
- Price
- Grit Range
- Grade Range
- Sizes
- Currency Exchange Rates

It dynamically calculates quotations for abrasive belts based on customer specifications while factoring in:
- Market-driven price changes
- Packaging and shipping costs
- Discount logic based on order quantities

The app significantly reduces manual calculation time and improves accuracy in quotation generation for customers.

---

## 🧠 Technologies Used

| Component | Technology |
|------------|-------------|
| **Programming Language** | Python |
| **Database (Local)** | SQLite (via DB Browser) |
| **Database (Cloud)** | [Turso](https://turso.tech) |
| **UI** | Python Tkinter |
| **Output** | Excel (.xlsx) for quotations |

---

## ⚙️ What is Turso?

**Turso** is a **serverless, distributed database platform** built on top of **SQLite**, designed for speed, scalability, and global access — especially for **edge and web applications**.  

Turso enables:
- 🌐 Instant sync between cloud and local clients  
- ⚡ Edge deployment for ultra-fast access  
- 🕒 Low-latency data retrieval  

In this project, Turso acts as the **cloud database backend**, ensuring product data remains accessible and synchronized across users and locations.

---

## 🧩 Features

### 🏗️ Functional Highlights
- Automates complex **pricing logic** for abrasive materials
- Calculates:
  - Number of belts created  
  - Offer price, discount, and final price  
  - Conversion from foreign currency to INR (based on exchange rate)
- Syncs **local (SQLite)** and **cloud (Turso)** data for consistency
- Provides a clean and integrated **user interface** for easy operation

### 💸 Pricing & Discount Logic
- If **Quantity > Belt Count** → 20% Discount  
- If **Quantity > 50% of Belt Count** → 15% Discount  
- Else → 10% Discount  

### 📦 Packaging & Shipping Multiplier
| Condition | Multiplier |
|------------|-------------|
| Width < 21mm or Length < 400mm | 5.0 |
| Width < 21mm or Length between 400–700mm | 4.0 |
| Default | 2.5 |

### 📏 Size Conversion
- If size is in **MM**, use directly  
- If size is in **M**, convert to **MM** before calculation

---

## 👤 User Access

The application supports role-based access:
- **Admin / Local User**:  
  - Manage product data (add, edit, delete materials)  
  - Update pricing details in both databases  
  - Export quotations to Excel  
- **General User**:  
  - Input customer specifications  
  - Generate quotations instantly  

---

## 📊 Output Example

The generated Excel file includes:
- Customer details  
- Product specifications (grit, grade, size, etc.)  
- Offer price, discount, and final quotation  
- Timestamp and company branding (optional)

---

## 🎯 Impact

- Reduced manual quotation time by **up to 60%**  
- Eliminated pricing errors due to human calculation  
- Improved workflow efficiency for the sales and operations team  
- Enabled real-time data access with Turso’s cloud-edge sync  

---


## 🪪 Author
**Rishabh Sunil Gaikwad**  
📧 [rishabh.gaikwad11122001@gmail.com](mailto:rishabh.gaikwad11122001@gmail.com)  
🔗 [LinkedIn](https://www.linkedin.com/in/rishabh-gaikwad-80a8a8218/)
