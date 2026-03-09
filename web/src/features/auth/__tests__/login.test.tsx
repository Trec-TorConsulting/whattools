import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "@/features/auth/pages/login";
import { renderWithProviders } from "@/test/test-utils";

describe("LoginPage", () => {

  it("renders login form", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows validation errors for empty form", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    });
  });

  it("submits with valid credentials", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(localStorage.getItem("whattools_access_token")).toBe("test-access-token");
    });
  });

  it("has link to register page", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText(/create one/i)).toBeInTheDocument();
  });

  it("has link to forgot password", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
  });
});
