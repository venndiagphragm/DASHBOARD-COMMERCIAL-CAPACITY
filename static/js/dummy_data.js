// Dummy Data for Pertamina Gas Customer Contracts
const customers = [
    {
        id: "CUST-001",
        name: "PT. Energi Abadi Jaya",
        region: "Jawa Barat",
        contractEnd: "2024-03-15",
        status: "urgent" // needs follow up
    },
    {
        id: "CUST-002",
        name: "CV. Makmur Sentosa",
        region: "Jawa Timur",
        contractEnd: "2024-06-20",
        status: "pending" // not yet followed up
    },
    {
        id: "CUST-003",
        name: "PT. Global Gas Industri",
        region: "Sumatera Selatan",
        contractEnd: "2024-02-01",
        status: "done" // followed up
    },
    {
        id: "CUST-004",
        name: "PT. Petro Kimia Utama",
        region: "Banten",
        contractEnd: "2024-04-10",
        status: "pending"
    },
    {
        id: "CUST-005",
        name: "PT. Sinar Mas Energy",
        region: "Jawa Barat",
        contractEnd: "2023-12-30",
        status: "urgent"
    },
    {
        id: "CUST-006",
        name: "CV. Bumi Gas Alam",
        region: "Kalimantan Timur",
        contractEnd: "2024-08-15",
        status: "done"
    }
];

// Helper to export if we were using modules, but for vanilla simple inclusion:
window.dummyCustomers = customers;
