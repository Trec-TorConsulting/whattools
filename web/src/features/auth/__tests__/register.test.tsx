import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RegisterPage } from "@/features/auth/pages/register";
import { renderWithProviders } from "@/test/test-utils";

describe("RegisterPage", () => {

  it("renders registration form", () => {
    renderWithProviders(<RegisterPage />);
    expect(screen.getByLabelText(/business name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows validation errors for empty submit", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />);

    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      const errors = screen.getAllByText(/at least/i);
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  it("submits valid registration and shows success", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />);

    await user.type(screen.getByLabelText(/full name/i), "Test User");
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/business name/i), "My Store");
    await user.type(screen.getByLabelText(/^password$/i), "password123456");
    await user.type(screen.getByLabelText(/confirm/i), "password123456");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });
  });

  it("has link to login page", () => {
    renderWithProviders(<RegisterPage />);
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });
});
